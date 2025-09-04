# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Optional
from layout import compute_layout, row_centers_from_positions

def build_viz(
    steps: List[List[int]],
    speed: int = 3,
    labels: Optional[List[str]] = None,
    split_index: Optional[int] = None,
    target_w: int = 800,
    target_h: int = 360,
    tall_mode: bool = False,
):
    params, positions, svg_w, svg_h = compute_layout(
        steps, target_w=target_w, target_h=target_h, tall_mode=tall_mode
    )
    if not params:
        return "<div></div>", [], 0

    cell_w = params["cell_w"]; cell_h = params["cell_h"]
    pad_x  = params["pad_x"];  pad_y  = params["pad_y"]
    rows   = params["rows"]
    min_left = params["min_left"]; max_right = params["max_right"]
    content_h = params["content_h"]

    # 애니메이션 타이밍
    scale = {1: 0.7, 2: 0.85, 3: 1.0, 4: 1.2, 5: 1.45}.get(int(speed), 1.0)
    dur_draw = 0.5/scale; dur_drop = 0.5/scale; pause = 0.22/scale
    row_span_ms = int((dur_draw + dur_drop + pause) * 1000)
    row_delay   = lambda r: (dur_draw + dur_drop + pause) * r
    d_line      = lambda ax,ay,bx,by: f"M {ax:.1f} {ay:.1f} L {bx:.1f} {by:.1f}"

    # 폰트/두께
    num_font   = max(24, int(cell_h * 0.42))
    label_font = max(16, int(cell_h * 0.35))
    line_w     = max(2.6, cell_w * 0.034)

    LABEL_OFFSET = max(18.0, cell_h * 0.40)

    # (기존) 콘텐츠 기반 패널 크기
    PANEL_INNER_PAD_X    = max(8.0, 0.012 * target_w)
    PANEL_INNER_PAD_Y_TOP = 24.0 + LABEL_OFFSET
    PANEL_INNER_PAD_Y_BOT = 40.0
    panel_w_content = (max_right - min_left) + PANEL_INNER_PAD_X*2
    panel_h_content = content_h + PANEL_INNER_PAD_Y_TOP + PANEL_INNER_PAD_Y_BOT

    # === 변경: 흰 배경 패널을 SVG 전체 폭/높이에 맞춤 ===
    panel_margin = max(8.0, 0.016 * svg_w)
    panel_x = panel_margin
    panel_y = panel_margin
    panel_w = max(panel_w_content, svg_w - panel_margin*2)
    panel_h = max(panel_h_content, svg_h - panel_margin*2)
    panel_rx = max(12.0, 0.018 * svg_w)

    css = f"""
    <style>
      .viz-wrap {{ height:100%; overflow:hidden; background:transparent; position:relative; padding:0; }}
      svg {{ width:100%; height:100%; display:block; }}  /* 컨테이너 높이에 100%로 스케일 */
      .panel {{ fill:#fffafb; stroke:#fecdd3; stroke-width:2; rx:{panel_rx:.1f}; ry:{panel_rx:.1f};
        filter: drop-shadow(0 4px 12px rgba(236,72,153,0.12)); }}
      .box {{ fill:url(#gbox); stroke:#fecdd3; rx:10; }}
      .bar {{ fill:url(#gbar); rx:5; }}
      .num {{ font-weight:800; font-size:{num_font}px; fill:#9d174d;
             paint-order:stroke; stroke:#fff; stroke-width:2px;
             text-anchor:middle; dominant-baseline:central; }}
      .label {{ font-weight:800; font-size:{label_font}px; fill:#be185d;
               text-anchor:middle; dominant-baseline:hanging; }}
      .line {{ stroke-width:{line_w:.2f}; fill:none; stroke-linecap:round; stroke-linejoin:round;
               stroke-dasharray:1; stroke-dashoffset:1; animation: draw {dur_draw:.2f}s ease both; }}
      @keyframes draw {{ to {{ stroke-dashoffset:0; }} }}
      @keyframes drop {{ from {{ transform: translateY(-18px); opacity:0; }} to {{ transform:none; opacity:1; }} }}
      @keyframes fadeout {{ to {{ opacity:0; }} }}
    </style>
    """

    defs_blocks = f"""
      <linearGradient id="gbox" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#fff1f2"/><stop offset="100%" stop-color="#ffe4e6"/>
      </linearGradient>
      <linearGradient id="gbar" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#fb7185"/><stop offset="100%" stop-color="#ec4899"/>
      </linearGradient>
      <clipPath id="panel-clip">
        <rect x="{panel_x:.1f}" y="{panel_y:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}"
              rx="{panel_rx:.1f}" ry="{panel_rx:.1f}"/>
      </clipPath>
    """

    # 첫 행
    nodes: List[str] = []
    centers = row_centers_from_positions(positions, cell_h, pad_y)
    labels = labels or []
    for i, v in enumerate(steps[0]):
        x, y = positions[0][i]
        bar_w = max(6, (v/9.0)*(cell_w*0.78))
        label_svg = ""
        if i < len(labels):
            lx = x + pad_x + cell_w/2
            ly = y + pad_y - LABEL_OFFSET
            label_svg = f'<text class="label" x="{lx:.1f}" y="{ly:.1f}">{labels[i]}</text>'
        nodes.append(f"""
        {label_svg}
        <g style="animation:drop {dur_drop:.2f}s ease both; animation-delay:{row_delay(0):.2f}s">
          <rect class="box" x="{x+pad_x:.1f}" y="{y+pad_y:.1f}" width="{cell_w:.1f}" height="{cell_h:.1f}"/>
          <rect class="bar" x="{x+pad_x+(cell_w-bar_w)/2:.1f}" y="{y+pad_y+cell_h-12:.1f}" width="{bar_w:.1f}" height="9"/>
          <text class="num" x="{x+pad_x+cell_w/2:.1f}" y="{y+pad_y+cell_h/2-5:.1f}">{v}</text>
        </g>""")

    # 연결선 + 하위 행
    defs_lines: List[str] = []
    lines_layers: List[str] = []
    gid = 0
    for r in range(1, rows):
        delay = row_delay(r)
        group = [f'<g style="animation: fadeout {pause:.2f}s linear both {delay+dur_draw+dur_drop:.2f}s">']
        for i, _ in enumerate(steps[r]):
            p1x,p1y = positions[r-1][i]
            p2x,p2y = positions[r-1][i+1]
            cx,cy   = positions[r][i]
            a1x,a1y = p1x+pad_x+cell_w/2, p1y+pad_y+cell_h/2
            a2x,a2y = p2x+pad_x+cell_w/2, p2y+pad_y+cell_h/2
            bx_l    = cx+pad_x+cell_w*0.35
            bx_r    = cx+pad_x+cell_w*0.65
            by_t    = cy+pad_y+cell_h*0.22
            gid += 1; g1 = f"gl{gid}"
            defs_lines.append(
                f'<linearGradient id="{g1}" gradientUnits="userSpaceOnUse" '
                f'x1="{a1x:.1f}" y1="{a1y:.1f}" x2="{bx_l:.1f}" y2="{by_t:.1f}">'
                f'<stop offset="0%" stop-color="#fbcfe8"/><stop offset="100%" stop-color="#ec4899"/></linearGradient>'
            )
            gid += 1; g2 = f"gl{gid}"
            defs_lines.append(
                f'<linearGradient id="{g2}" gradientUnits="userSpaceOnUse" '
                f'x1="{a2x:.1f}" y1="{a2y:.1f}" x2="{bx_r:.1f}" y2="{by_t:.1f}">'
                f'<stop offset="0%" stop-color="#fbcfe8"/><stop offset="100%" stop-color="#ec4899"/></linearGradient>'
            )
            group.append(f'<path class="line" style="animation-delay:{delay:.2f}s" d="{d_line(a1x,a1y,bx_l,by_t)}" stroke="url(#{g1})" pathLength="1"/>')
            group.append(f'<path class="line" style="animation-delay:{delay:.2f}s" d="{d_line(a2x,a2y,bx_r,by_t)}" stroke="url(#{g2})" pathLength="1"/>')
        group.append('</g>')
        lines_layers.append("".join(group))

        for i, v in enumerate(steps[r]):
            cx, cy = positions[r][i]
            bar_w = max(6, (v/9.0)*(cell_w*0.78))
            nodes.append(f"""
            <g style="animation:drop {dur_drop:.2f}s ease both; animation-delay:{(delay+dur_draw):.2f}s">
              <rect class="box" x="{cx+pad_x:.1f}" y="{cy+pad_y:.1f}" width="{cell_w:.1f}" height="{cell_h:.1f}"/>
              <rect class="bar" x="{cx+pad_x+(cell_w-bar_w)/2:.1f}" y="{cy+pad_y+cell_h-12:.1f}" width="{bar_w:.1f}" height="9"/>
              <text class="num" x="{cx+pad_x+cell_w/2:.1f}" y="{cy+pad_y+cell_h/2-5:.1f}">{v}</text>
            </g>""")

    html = f"""
    {css}
    <div class="viz-wrap">
      <svg viewBox="0 0 {svg_w:.1f} {max(svg_h, panel_h):.1f}" preserveAspectRatio="xMidYMid meet">
        <defs>
          {defs_blocks}
          {''.join(defs_lines)}
        </defs>
        <rect class="panel" x="{panel_x:.1f}" y="{panel_y:.1f}"
              width="{panel_w:.1f}" height="{panel_h:.1f}" rx="{panel_rx:.1f}" ry="{panel_rx:.1f}"/>
        <g clip-path="url(#panel-clip)">
          {''.join(lines_layers)}
          {''.join(nodes)}
        </g>
      </svg>
    </div>
    """
    centers = row_centers_from_positions(positions, cell_h, pad_y)
    return html, centers, row_span_ms
