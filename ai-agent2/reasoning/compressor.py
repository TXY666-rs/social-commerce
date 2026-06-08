"""工具输出压缩器 — 减少喂给 LLM 的 Token 消耗

设计思路：
    工具返回的数据是给"前端展示"设计的（完整、详细），
    但 LLM 只需要"足够理解"的信息量。压缩器在 guard 节点中
    把长输出压缩后再喂给 LLM，减少 token 消耗。

压缩策略：
    列表类（get_my_orders, search_products, get_my_coupons）：
        → 截断到前 3 条 + 末尾加"共N条，显示前3条"
    详情类（get_goods_detail, track_logistics）：
        → 去掉空字段和多余空行
    结果类（cancel_order, request_refund, claim_coupon）：
        → 不压缩（本来就短）

关键约束：
    ① 内部标记 <!-- internal_ids:... --> 必须保留（代码需要）
    ② 压缩只影响 LLM 看到的内容，不影响工具原始返回值
    ③ 压缩器不知道工具名，只根据内容特征判断类型
"""

import re
import structlog

logger = structlog.get_logger(__name__)

# 列表类工具输出的最大条目数
MAX_LIST_ITEMS = 3

# 压缩触发的最小行数（低于此行数不压缩）
MIN_LINES_TO_COMPRESS = 8


def compress_tool_output(content: str, tool_name: str = "") -> str:
    """压缩工具输出。

    Args:
        content: 工具原始输出
        tool_name: 工具名（可选，用于日志）

    Returns:
        压缩后的输出（如果没有触发压缩，原样返回）
    """
    if not content:
        return content

    lines = content.split("\n")

    # 低于阈值不压缩
    if len(lines) < MIN_LINES_TO_COMPRESS:
        return content

    # 提取内部标记（<!-- internal_ids:... -->）
    internal_marker = ""
    clean_lines = []
    for line in lines:
        if line.strip().startswith("<!-- internal_ids:"):
            internal_marker = line.strip()
        else:
            clean_lines.append(line)

    # 尝试列表压缩
    compressed = _try_list_compress(clean_lines)

    # 恢复内部标记
    if internal_marker:
        compressed = compressed + "\n" + internal_marker

    if compressed != content:
        original_len = len(content)
        compressed_len = len(compressed)
        ratio = compressed_len / original_len if original_len > 0 else 1
        logger.info("tool_output_compressed",
                     tool=tool_name,
                     original_lines=len(lines),
                     compressed_lines=len(compressed.split("\n")),
                     ratio=f"{ratio:.0%}")

    return compressed


def _try_list_compress(lines: list[str]) -> str:
    """尝试列表压缩：识别序号行，截断到前 N 条。

    序号行特征：
    - 【1】/ 【2】（get_my_orders 格式）
    - 1. / 2. / 3.（search_products 格式）
    - - 第1条 / - 第2条
    """
    # 识别序号行的正则
    item_pattern = re.compile(r'^(【\d+】|\d+\.\s|-\s第\d+条)')
    header_lines = []    # 标题行（序号行之前的内容）
    item_lines = []      # 序号行及其附属行
    footer_lines = []    # 脚注行（序号行之后的非序号内容）

    current_section = "header"
    current_item_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_section == "item":
                current_item_lines.append(line)
            elif current_section == "footer":
                footer_lines.append(line)
            continue

        if item_pattern.match(stripped):
            if current_section == "header":
                current_section = "item"
            elif current_section == "footer":
                # 又出现序号行，说明不是真正的 footer，合并回 item
                current_section = "item"
                if footer_lines:
                    current_item_lines.extend(footer_lines)
                    footer_lines = []

            if current_item_lines:
                item_lines.append(current_item_lines)
            current_item_lines = [line]
        elif current_section == "item":
            # 序号行的附属行（时间信息、描述等）
            if line.startswith("   ") or line.startswith("\t"):
                current_item_lines.append(line)
            else:
                # 非缩进行，可能是 footer
                current_section = "footer"
                if current_item_lines:
                    item_lines.append(current_item_lines)
                    current_item_lines = []
                footer_lines.append(line)
        elif current_section == "header":
            header_lines.append(line)
        elif current_section == "footer":
            footer_lines.append(line)

    # 处理最后一组
    if current_item_lines:
        if current_section == "item":
            item_lines.append(current_item_lines)
        else:
            footer_lines.extend(current_item_lines)

    # 没有识别到列表项，不压缩
    if not item_lines:
        return "\n".join(lines)

    total_items = len(item_lines)

    # 低于阈值不压缩
    if total_items <= MAX_LIST_ITEMS:
        return "\n".join(lines)

    # 截断
    kept_items = item_lines[:MAX_LIST_ITEMS]
    truncated_count = total_items - MAX_LIST_ITEMS

    result_lines = []
    result_lines.extend(header_lines)
    for item_group in kept_items:
        result_lines.extend(item_group)
    result_lines.append(f"（共 {total_items} 条，此处显示前 {MAX_LIST_ITEMS} 条，其余省略）")
    result_lines.extend(footer_lines)

    return "\n".join(result_lines)
