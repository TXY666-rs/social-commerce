"""评估框架 — 多 Skill + 单 Agent 架构

评估维度：
- Skill 命中率：关键词触发的 Skill 是否正确
- 回复质量：关键词覆盖 + 禁止词检测
- 工具调用：期望工具是否被调用
- 安全拦截：注入/越狱是否被拦截

架构说明：
  Skill 优先匹配 → 未命中的请求交给单个 React Agent 处理
  不再有多 Agent 路由，因此不检查 agent_type

路由分组（route）：
  按实际路由路径分组，直接反映系统的路由决策质量
  - 具体 skill 名（track_order, return_item 等）：Skill 触发
  - faq：FAQ 优先匹配命中
  - agent：未命中任何 Skill/FAQ，交给 ReAct Agent
  - safety：被安全模块拦截

使用方式：
    python -m monitoring.eval.runner
    python -m monitoring.eval.runner --route track_order
"""

import json
import time
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


# ============================================================
# 评估指标定义
# ============================================================

@dataclass
class EvalMetrics:
    """单次评估指标"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    accuracy: float = 0.0
    avg_latency_ms: float = 0.0
    tool_call_accuracy: float = 0.0      # 工具调用正确率
    task_completion_rate: float = 0.0    # 任务完成率
    hallucination_rate: float = 0.0      # 幻觉率
    skill_accuracy: float = 0.0          # 技能匹配准确率
    skill_total: int = 0                 # 设置了 expected_skill 的用例总数
    skill_matched_count: int = 0         # 技能匹配正确的用例数
    by_skill: dict = field(default_factory=dict)   # 按技能分组统计
    by_route: dict = field(default_factory=dict)   # 按路由分组统计


@dataclass
class TestCase:
    """单个测试用例"""
    id: str
    message: str                                              # 用户输入
    expected_keywords: list[str] = field(default_factory=list)  # 回复中应包含的关键词
    forbidden_keywords: list[str] = field(default_factory=list) # 回复中不应包含的关键词
    expected_tools: list[str] = field(default_factory=list)     # 期望调用的工具
    expected_skill: Optional[str] = None                        # 期望命中的技能（null = 不触发 Skill，交给 Agent）
    route: str = "agent"                                        # 路由分类（skill名/faq/agent/safety）
    difficulty: str = "easy"                                    # easy / medium / hard
    should_block: bool = False                                  # 是否期望被安全模块拦截


@dataclass
class EvalResult:
    """单条评估结果"""
    case: TestCase
    passed: bool
    keywords_matched: list[str] = field(default_factory=list)
    keywords_missed: list[str] = field(default_factory=list)
    forbidden_found: list[str] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    skill_matched: bool = False
    expected_skill_name: str = ""
    actual_skill_name: str = ""
    reply: str = ""
    latency_ms: float = 0.0
    error: Optional[str] = None


# ============================================================
# 数据集加载
# ============================================================

def load_test_cases(path: str) -> list[TestCase]:
    """从 JSON 文件加载测试用例"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cases = []
    for item in data:
        cases.append(TestCase(
            id=item["id"],
            message=item["message"],
            expected_keywords=item.get("expected_keywords", []),
            forbidden_keywords=item.get("forbidden_keywords", []),
            expected_tools=item.get("expected_tools", []),
            expected_skill=item.get("expected_skill", None),
            route=item.get("route", "agent"),
            difficulty=item.get("difficulty", "easy"),
            should_block=item.get("should_block", False),
        ))
    return cases


# ============================================================
# 评估逻辑
# ============================================================

def evaluate_reply(case: TestCase, reply: str,
                   tools_called: list[str], latency_ms: float,
                   skill_name: str = "") -> EvalResult:
    """评估单条回复

    架构：Skill 优先 → 单 Agent 兜底
    - expected_skill 不为 null：检查 Skill 是否正确触发
    - expected_skill 为 null：不检查 Skill（由 Agent 处理），只检查回复质量
    """
    reply_lower = reply.lower()

    # 1. 技能匹配检查
    skill_matched = False
    if case.expected_skill is not None:
        skill_matched = (skill_name == case.expected_skill)

    # 2. 关键词匹配
    keywords_matched = []
    keywords_missed = []
    for kw in case.expected_keywords:
        if kw.lower() in reply_lower:
            keywords_matched.append(kw)
        else:
            keywords_missed.append(kw)

    # 3. 禁止词检测
    forbidden_found = []
    for kw in case.forbidden_keywords:
        if kw.lower() in reply_lower:
            forbidden_found.append(kw)

    # 4. 工具调用检查
    tools_matched = [t for t in case.expected_tools if t in tools_called]

    # 5. 综合判断
    #    Skill 用例：skill 必须匹配 + 关键词 + 禁止词
    #    Agent 用例：只检查关键词 + 禁止词
    passed = (
        len(keywords_missed) == 0
        and len(forbidden_found) == 0
    )
    if case.expected_skill is not None:
        passed = passed and skill_matched

    return EvalResult(
        case=case,
        passed=passed,
        keywords_matched=keywords_matched,
        keywords_missed=keywords_missed,
        forbidden_found=forbidden_found,
        tools_called=tools_called,
        skill_matched=skill_matched,
        expected_skill_name=case.expected_skill or "",
        actual_skill_name=skill_name,
        reply=reply,
        latency_ms=latency_ms,
    )


def compute_metrics(results: list[EvalResult]) -> EvalMetrics:
    """汇总评估指标"""
    m = EvalMetrics()
    m.total = len(results)
    m.passed = sum(1 for r in results if r.passed)
    m.failed = m.total - m.passed
    m.accuracy = m.passed / m.total if m.total > 0 else 0
    m.avg_latency_ms = sum(r.latency_ms for r in results) / m.total if m.total > 0 else 0

    # 工具调用正确率（严格匹配：期望工具必须全部被调用）
    tool_checks = 0
    tool_passes = 0
    for r in results:
        expected = set(r.case.expected_tools)
        actual = set(r.tools_called)
        if expected:
            tool_checks += 1
            if expected.issubset(actual):
                tool_passes += 1
    m.tool_call_accuracy = tool_passes / tool_checks if tool_checks > 0 else 1.0

    # 任务完成率（有工具调用 = 完成任务）
    completed = sum(1 for r in results if len(r.tools_called) > 0 and r.passed)
    m.task_completion_rate = completed / m.total if m.total > 0 else 0

    # 幻觉率（回复中出现了禁用关键词）
    hallucinated = sum(1 for r in results if len(r.forbidden_found) > 0)
    m.hallucination_rate = hallucinated / m.total if m.total > 0 else 0

    # 技能匹配统计
    skill_results = [r for r in results if r.case.expected_skill is not None]
    m.skill_total = len(skill_results)
    m.skill_matched_count = sum(1 for r in skill_results if r.skill_matched)
    m.skill_accuracy = m.skill_matched_count / m.skill_total if m.skill_total > 0 else 1.0

    # 按技能分组
    skill_grouped: dict[str, list[EvalResult]] = {}
    for r in skill_results:
        skill_name = r.case.expected_skill or ""
        skill_grouped.setdefault(skill_name, []).append(r)
    for skill_name, srs in skill_grouped.items():
        m.by_skill[skill_name] = {
            "total": len(srs),
            "matched": sum(1 for r in srs if r.skill_matched),
            "accuracy": sum(1 for r in srs if r.skill_matched) / len(srs) if srs else 0,
        }

    # 按路由分组
    route_results: dict[str, list[EvalResult]] = {}
    for r in results:
        route = r.case.route
        route_results.setdefault(route, []).append(r)
    for route, rrs in route_results.items():
        m.by_route[route] = {
            "total": len(rrs),
            "passed": sum(1 for r in rrs if r.passed),
            "accuracy": sum(1 for r in rrs if r.passed) / len(rrs) if rrs else 0,
        }

    return m


def generate_report(results: list[EvalResult], metrics: EvalMetrics, output_path: str) -> None:
    """生成评估报告"""
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total": metrics.total,
            "passed": metrics.passed,
            "failed": metrics.failed,
            "accuracy": round(metrics.accuracy, 4),
            "avg_latency_ms": round(metrics.avg_latency_ms, 2),
            "tool_call_accuracy": round(metrics.tool_call_accuracy, 4),
            "task_completion_rate": round(metrics.task_completion_rate, 4),
            "hallucination_rate": round(metrics.hallucination_rate, 4),
            "skill_accuracy": round(metrics.skill_accuracy, 4),
            "skill_total": metrics.skill_total,
            "skill_matched_count": metrics.skill_matched_count,
            "by_route": metrics.by_route,
            "by_skill": metrics.by_skill,
        },
        "details": [],
    }

    for r in results:
        # 计算实际路由：有 skill 命中 → skill 名，否则 → agent
        actual_route = r.actual_skill_name if r.actual_skill_name else "agent"
        report["details"].append({
            "id": r.case.id,
            "message": r.case.message,
            "route": r.case.route,
            "actual_route": actual_route,
            "difficulty": r.case.difficulty,
            "passed": r.passed,
            "skill_matched": r.skill_matched,
            "expected_skill_name": r.expected_skill_name,
            "keywords_missed": r.keywords_missed,
            "forbidden_found": r.forbidden_found,
            "latency_ms": round(r.latency_ms, 2),
            "reply_preview": r.reply[:200],
            "error": r.error,
        })

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 打印摘要
    print(f"\n{'='*60}")
    print(f"  评估报告 — {report['generated_at']}")
    print(f"{'='*60}")
    print(f"  总计: {metrics.total}  通过: {metrics.passed}  失败: {metrics.failed}")
    print(f"  端到端准确率: {metrics.accuracy:.1%}")
    print(f"  Skill 命中率: {metrics.skill_accuracy:.1%} ({metrics.skill_matched_count}/{metrics.skill_total})")
    print(f"  工具调用正确率: {metrics.tool_call_accuracy:.1%}")
    print(f"  任务完成率: {metrics.task_completion_rate:.1%}")
    print(f"  幻觉率: {metrics.hallucination_rate:.1%}")
    print(f"  平均延迟: {metrics.avg_latency_ms:.0f}ms")
    print(f"{'='*60}")
    if metrics.by_route:
        print("  按路由:")
        for route, stats in metrics.by_route.items():
            print(f"    {route}: {stats['accuracy']:.1%} ({stats['passed']}/{stats['total']})")
    if metrics.by_skill:
        print("  按技能:")
        for skill_name, stats in metrics.by_skill.items():
            print(f"    {skill_name}: {stats['accuracy']:.1%} ({stats['matched']}/{stats['total']})")
    print(f"{'='*60}\n")
    print(f"  详细报告已保存至: {output_path}")
