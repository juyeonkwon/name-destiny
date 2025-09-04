from __future__ import annotations
from typing import List, Tuple, Dict

def compute_layout(
    steps: List[List[int]],
    target_w: int = 1000,
    target_h: int = 560,
    tall_mode: bool = False,
) -> tuple[Dict[str, float], List[List[tuple[float, float]]], float, float]:
    if not steps or not steps[0]:
        return {}, [], float(target_w), float(target_h)

    rows = len(steps)
    max_cols = len(steps[0])

    # 외곽 패딩
    outer_pad_x = max(16.0, target_w * 0.04)
    outer_pad_y = max(16.0, target_h * 0.06)

    # Tall 모드 시 세로 여유 확대
    base_vgap_ratio = 0.03
    vgap = max(8.0, target_h * (0.05 if tall_mode else base_vgap_ratio))

    avail_w = max(120.0, target_w - outer_pad_x * 2)
    avail_h = max(160.0, target_h - outer_pad_y * 2)

    cell_w_by_width  = avail_w / max(1, max_cols)
    cell_h_by_height = (avail_h - vgap * (rows - 1)) / max(1, rows)

    cell_w = max(56.0, min(120.0, cell_w_by_width * 0.9))
    cell_h_base = cell_h_by_height * (1.10 if tall_mode else 0.90)
    cell_h = max(56.0, min(120.0, cell_h_base))

    content_w = cell_w * max_cols
    content_h = cell_h * rows + vgap * (rows - 1)

    pad_x = (target_w - content_w) / 2.0
    pad_y = (target_h - content_h) / 2.0

    positions: List[List[Tuple[float, float]]] = []
    min_left = float("inf")
    max_right = float("-inf")

    for r in range(rows):
        cols = len(steps[r])
        row_w = cell_w * cols
        row_left = (target_w - row_w) / 2.0
        y = r * (cell_h + vgap)
        row_pos: List[Tuple[float, float]] = []
        for c in range(cols):
            x = row_left + c * cell_w - pad_x
            row_pos.append((x, y))
            min_left = min(min_left, x)
            max_right = max(max_right, x + cell_w)
        positions.append(row_pos)

    params = {
        "cell_w": cell_w,
        "cell_h": cell_h,
        "pad_x": pad_x,
        "pad_y": pad_y,
        "rows": rows,
        "min_left": min_left,
        "max_right": max_right,
        "content_h": content_h,
    }

    svg_w = float(target_w)
    svg_h = float(max(target_h, content_h + pad_y * 2))
    return params, positions, svg_w, svg_h


def row_centers_from_positions(
    positions: List[List[Tuple[float, float]]],
    cell_h: float,
    pad_y: float,
) -> List[float]:
    centers: List[float] = []
    for row in positions:
        if not row:
            centers.append(pad_y)
            continue
        y = row[0][1] + pad_y + cell_h / 2.0
        centers.append(y)
    return centers
