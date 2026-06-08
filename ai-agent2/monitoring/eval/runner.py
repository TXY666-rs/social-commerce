"""评估执行器 — 调用 /chat 接口执行批量评估

架构：多 Skill + 单 Agent（Skill 优先，Agent 兜底）
评估维度：Skill 命中率 + 回复质量 + 安全拦截

使用方式：
    python -m monitoring.eval.runner                    # 运行全部用例
    python -m monitoring.eval.runner --domain order      # 只运行订单领域
    python -m monitoring.eval.runner --difficulty easy   # 只运行简单用例
    python -m monitoring.eval.runner --report report.json # 输出报告到文件
"""

import asyncio
import argparse
import time
from pathlib import Path

import httpx

from monitoring.eval.evaluator import (
    TestCase, EvalResult,
    load_test_cases, evaluate_reply, compute_metrics, generate_report,
)

API_BASE = "http://localhost:8000"
API_URL = f"{API_BASE}/chat"
TIMEOUT = 30.0

# 评估专用用户 ID（使用真实用户数据，确保 Skill 可正常查询）
EVAL_USER_ID = "1"


def filter_cases(
    cases: list[TestCase],
    domain: str | None = None,
    difficulty: str | None = None,
) -> list[TestCase]:
    """按领域/难度筛选测试用例"""
    result = []
    for tc in cases:
        if domain and tc.domain != domain:
            continue
        if difficulty and tc.difficulty != difficulty:
            continue
        result.append(tc)
    return result


async def run_single_test(
    client: httpx.AsyncClient,
    test_case: TestCase,
    auth_token: str | None = None,
    eval_user_id: str = EVAL_USER_ID,
) -> EvalResult:
    """执行单条测试用例，返回评估结果"""
    # 每条用例使用独立 session_id，避免 Skill 状态在多条用例间串扰
    unique_session_id = f"eval_{test_case.id}_{time.monotonic_ns()}"
    payload = {"message": test_case.message, "session_id": unique_session_id}

    headers = {"X-User-Id": eval_user_id}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    t0 = time.monotonic()
    try:
        response = await client.post(API_URL, json=payload, headers=headers, timeout=TIMEOUT)
        latency_ms = (time.monotonic() - t0) * 1000

        # 安全用例：期望被拦截（HTTP 400 = 注入被成功阻止）
        if test_case.should_block:
            blocked = response.status_code == 400
            return EvalResult(
                case=test_case,
                passed=blocked,
                reply=response.text[:200] if not blocked else "blocked",
                latency_ms=latency_ms,
                error=None if blocked else f"期望被拦截但返回 HTTP {response.status_code}",
            )

        if response.status_code == 200:
            data = response.json()
            reply = data.get("reply", "")
            actual_tools = data.get("tools_called", [])
            actual_skill = data.get("skill_name", "")

            return evaluate_reply(
                case=test_case,
                reply=reply,
                tools_called=actual_tools,
                latency_ms=latency_ms,
                skill_name=actual_skill,
            )
        else:
            return EvalResult(
                case=test_case,
                passed=False,
                reply=f"HTTP {response.status_code}",
                latency_ms=latency_ms,
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        latency_ms = (time.monotonic() - t0) * 1000
        return EvalResult(
            case=test_case,
            passed=False,
            reply="",
            latency_ms=latency_ms,
            error=str(e)[:200],
        )


async def run_evaluation(
    domain: str | None = None,
    difficulty: str | None = None,
    report_path: str | None = None,
    auth_token: str | None = None,
    eval_user_id: str = EVAL_USER_ID,
) -> dict:
    """运行完整评估流程"""
    cases_path = str(Path(__file__).parent / "test_cases.json")
    all_cases = load_test_cases(cases_path)
    test_cases = filter_cases(all_cases, domain, difficulty)

    if not test_cases:
        print("未找到匹配的测试用例")
        return {}

    print(f"加载 {len(test_cases)} 条测试用例...")
    if domain:
        print(f"  领域筛选: {domain}")
    if difficulty:
        print(f"  难度筛选: {difficulty}")
    print(f"  评估用户ID: {eval_user_id}")
    if auth_token:
        print(f"  认证: 已配置 token")
    else:
        print(f"  认证: 使用 X-User-Id 头")

    results: list[EvalResult] = []
    async with httpx.AsyncClient() as client:
        for i, tc in enumerate(test_cases):
            result = await run_single_test(client, tc, auth_token=auth_token, eval_user_id=eval_user_id)
            results.append(result)
            status = "✓" if result.passed else "✗"
            print(f"  [{i+1}/{len(test_cases)}] {status} {tc.id}: {tc.message[:40]}")

    metrics = compute_metrics(results)
    output_path = report_path or "eval/eval_report.json"
    generate_report(results, metrics, output_path)

    # 打印 bad cases
    bad_cases = [r for r in results if not r.passed]
    if bad_cases:
        print(f"\n{'='*60}")
        print(f"失败用例 ({len(bad_cases)} 条):")
        print(f"{'='*60}")
        for r in bad_cases[:20]:
            reason = r.error or ""
            if not reason:
                if r.case.expected_skill is not None and not r.skill_matched:
                    reason = f"Skill不匹配: 期望={r.case.expected_skill}"
                elif r.keywords_missed:
                    reason = f"缺少关键词: {r.keywords_missed}"
                elif r.forbidden_found:
                    reason = f"包含禁止词: {r.forbidden_found}"
                else:
                    reason = "未知原因"
            print(f"  [{r.case.id}] {reason}")

    return {"total": metrics.total, "passed": metrics.passed, "accuracy": metrics.accuracy}


def main():
    parser = argparse.ArgumentParser(description="AI Agent 评估执行器")
    parser.add_argument("--domain", type=str, help="按领域筛选: order/product/after_sale/coupon/safety/faq")
    parser.add_argument("--difficulty", type=str, help="按难度筛选: easy/medium/hard")
    parser.add_argument("--report", type=str, help="报告输出路径 (JSON)")
    parser.add_argument("--token", type=str, help="认证 token（避免 401 错误）")
    args = parser.parse_args()

    asyncio.run(run_evaluation(
        domain=args.domain,
        difficulty=args.difficulty,
        report_path=args.report,
        auth_token=args.token,
    ))


if __name__ == "__main__":
    main()
