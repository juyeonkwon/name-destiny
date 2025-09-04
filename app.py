from __future__ import annotations
import re, webbrowser
import gradio as gr

from name_core import (
    interleave_names, expand_reduction_steps, hangul_syllables,
    name_to_strokes, fortune_from_last_digit
)
from name_svg import build_viz

# ---------- utils ---------- #
def _make_steps_and_labels(name1: str, name2: str):
    if not name1.strip() or not name2.strip():
        return None, None, None, "⚠️ 두 사람 이름을 모두 입력하세요."
    full = interleave_names(name1, name2)
    stroke_row = [s % 10 for s in name_to_strokes(full)]
    if len(stroke_row) < 2:
        return None, None, None, "⚠️ 최소 2글자 이상 입력하세요."
    steps = expand_reduction_steps(stroke_row)
    labels = list(hangul_syllables(full))[: len(steps[0])]
    return steps, labels, None, None

def _final_number(steps: list[list[int]]) -> list[str]:
    if not steps: return []
    return [str(x) for x in steps[-1]]

def _inject_percent(viz_html: str, centers, row_span_ms: int) -> str:
    """
    2단계 애니메이션 종료 직후, 최종 오른쪽 숫자 '박스 바깥 오른쪽'에 %를 표시(페이드인).
    - 위치: 마지막 <rect class="box"...>의 x+width+gap
    - 진하게: fill-opacity 0.82
    """
    try:
        # 애니 종료 후 약간의 여유
        rows = len(centers) if centers else 0
        delay_ms = int(rows * (row_span_ms or 0) + 400)

        # 마지막 숫자 텍스트(정렬용 y 좌표)
        m_num_all = list(re.finditer(
            r'<text\s+class="num"\s+x="([0-9.]+)"\s+y="([0-9.]+)">(\d)</text>', viz_html))
        if not m_num_all:
            return viz_html
        m_num = m_num_all[-1]
        num_y = float(m_num.group(2))

        # 마지막 셀 박스(오른쪽 최종 칸)의 x, width 추출
        m_rect_all = list(re.finditer(
            r'<rect\s+class="box"\s+x="([0-9.]+)"\s+y="([0-9.]+)"\s+width="([0-9.]+)"\s+height="([0-9.]+)"',
            viz_html))
        if m_rect_all:
            r = m_rect_all[-1]
            rect_x = float(r.group(1))
            rect_w = float(r.group(3))
            pct_x = rect_x + rect_w + 14.0   # 박스 '바깥'으로 14px 띄움
        else:
            # 혹시 못 찾으면 숫자 x 기준으로 우측 24px
            pct_x = float(m_num.group(1)) + 24.0

        # % 요소 (더 진하게: opacity 최종 .82, 사이즈 30px)
        pct_svg = (
            f'<text x="{pct_x:.1f}" y="{num_y:.1f}" text-anchor="start" '
            f'dominant-baseline="middle" style="opacity:0; '
            f'animation:vizPctIn .9s ease {delay_ms}ms forwards; '
            f'font-weight:900; font-size:30px; fill:#be185d; fill-opacity:.82; '
            f'pointer-events:none;">%</text>'
        )

        # 마지막 숫자 바로 뒤에 삽입
        injected = viz_html[:m_num.end()] + pct_svg + viz_html[m_num.end():]

        # 키프레임을 SVG 내부에 추가
        idx = injected.rfind('</svg>')
        if idx != -1:
            injected = (injected[:idx] +
                        '<style>@keyframes vizPctIn{from{opacity:0}to{opacity:.82}}</style>' +
                        injected[idx:])
        return injected
    except Exception:
        return viz_html


# ---------- CSS ---------- #
GLOBAL_CSS = """
<style>
  :root {
    --pink-100:#fff0f6; --pink-200:#ffe4e6; --pink-300:#fda4af;
    --pink-400:#fb7185; --pink-500:#f43f5e; --pink-600:#e11d48;
    --pink-700:#be185d; --pink-800:#9d174d;
  }
  body {
    background: linear-gradient(135deg, var(--pink-100), #fff 50%, var(--pink-100));
    font-family: "Pretendard","Noto Sans KR",sans-serif;
  }
  .wizard-frame { max-width: 760px; margin: 24px auto; }

  .glass-card {
    backdrop-filter: blur(10px); background: rgba(255,255,255,.7);
    border: 1px solid var(--pink-200); border-radius: 18px; padding: 18px;
    box-shadow: 0 6px 20px rgba(236,72,153,.15);
  }
  .pink-title { font-weight:900; font-size:22px; color:var(--pink-700); text-align:center; margin-bottom:6px; }
  .pink-btn {
    background: linear-gradient(180deg, var(--pink-500), var(--pink-600)) !important;
    color:#fff !important; font-weight:700 !important; border:none !important; border-radius:10px !important;
    padding:10px 16px !important; box-shadow: 0 4px 12px rgba(244,63,94,.25); transition:all .2s ease;
  }
  .pink-btn:hover { transform: translateY(-2px); }
  .pink-help { color:var(--pink-600); font-weight:500; margin-top:10px; font-size:14px; text-align:center; }

  /* 패널 고정(520px), 스크롤 없음 — 계산/입력 화면 크기 그대로 */
  .panel {
    background:#fff; border-radius:18px; padding:16px;
    box-shadow:0 8px 28px rgba(236,72,153,.18);
    height:520px; max-height:520px; overflow:hidden;
  }
  /* 계산 SVG만 패널에 꽉 채움 (하트에는 영향 없음) */
  .panel .viz-wrap > svg { width:100% !important; height:100% !important; display:block; }

  /* ====== 결과 카드(세로 확장) ====== */
  .result-wrap {
    height:100%; display:flex; align-items:center; justify-content:center;
  }
  .result-card {
    display:flex; flex-direction:column; align-items:center; justify-content:center; gap:12px;
    width:clamp(520px, 86%, 700px);
    min-height:420px; /* 3단계 카드만 여유롭게 */
    padding:22px 24px; border:2px solid #fecdd3; border-radius:16px;
    background:#fffafb; box-shadow:0 8px 22px rgba(236,72,153,.12);
  }
  .result-card .final-heart { text-align:center; margin:0; }
  .result-card .final-heart svg { width:140px; height:auto; }

  .score-chip {
    font-weight:900; color:#be185d; font-size:18px;
  }
  .desc-box {
    padding:12px 14px; border:2px solid #fda4af; border-radius:12px;
    background:#fff0f6; color:#9d174d; line-height:1.4; text-align:center;
    width:92%;
  }

  .nav-bar { display:flex; gap:10px; justify-content:center; margin-top:12px; }
</style>
"""

# ---------- UI ---------- #
def launch():
    with gr.Blocks(title="이름 궁합 • Wizard", fill_height=False) as demo:
        gr.HTML(GLOBAL_CSS)
        with gr.Column(elem_classes=["wizard-frame"]):
            with gr.Group(elem_classes=["glass-card"]):
                gr.HTML("<div class='pink-title'>💕 이름 궁합 계산기 💕</div>")

                step_idx        = gr.State(1)   # 1=입력, 2=계산, 3=결과
                viz_html_state  = gr.State("")
                final_svg_state = gr.State("")
                last_digit_state= gr.State(0)

                with gr.Group(elem_classes=["panel"]):
                    # 1. 입력
                    step1 = gr.Column(visible=True)
                    with step1:
                        name1 = gr.Textbox(label="이름 1", placeholder="예: 김철수")
                        name2 = gr.Textbox(label="이름 2", placeholder="예: 김영희")
                        speed = gr.Slider(1, 5, step=1, value=3, label="애니메이션 속도")
                        gr.Markdown("**규칙:** 두 이름을 번갈아 쓰고, 획수를 합산해 1의 자리만 남겨 최종 2자리까지 계산합니다.", elem_classes=["pink-help"])

                    # 2. 계산(애니메이션)
                    step2 = gr.Column(visible=False)
                    with step2:
                        calc_view = gr.HTML(value="")

                    # 3. 결과
                    step3 = gr.Column(visible=False)
                    with step3:
                        final_heart  = gr.HTML(label="최종 궁합 수", value="")
                        fortune_text = gr.HTML(value="")

                with gr.Row(elem_classes=["nav-bar"]):
                    btn_prev  = gr.Button("← 이전", elem_classes=["pink-btn"], visible=False)
                    btn_next  = gr.Button("다음 →", elem_classes=["pink-btn"], visible=True)
                    btn_reset = gr.Button("처음으로", elem_classes=["pink-btn"], visible=False)

        # ---------- 전환 ---------- #
        def on_next(cur_step, n1, n2, spd, v_html, f_svg, last_d):
            # 1 -> 2
            if cur_step == 1:
                made = _make_steps_and_labels(n1, n2)
                if not made or not made[0]:
                    err = made[3] if made and len(made) > 3 else "⚠️ 두 사람 이름을 모두 입력하세요."
                    return (
                        1,
                        gr.update(visible=True), gr.update(visible=False), gr.update(visible=False),
                        gr.update(value=f"<div style='padding:12px;color:#a00;font-weight:700;'>{err}</div>"),
                        v_html, f_svg, last_d,
                        gr.update(value=""), gr.update(value=""),
                        gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
                    )

                steps, labels, split_idx, _ = made
                panel_h, target_w = 520, 720
                target_h = max(400, panel_h - 64)

                # build_viz → 퍼센트 주입
                viz_html, centers, row_span_ms = build_viz(
                    steps=steps, speed=int(spd), labels=labels,
                    split_index=split_idx, target_w=int(target_w), target_h=int(target_h),
                    tall_mode=False
                )
                viz_html = _inject_percent(viz_html, centers, row_span_ms)

                finals = _final_number(steps)
                if len(finals) == 2:
                    num_str = finals[0] + finals[1]
                    final_svg = f"""
                    <div class='final-heart'>
                      <svg viewBox="0 0 200 180" xmlns="http://www.w3.org/2000/svg">
                        <defs><linearGradient id="gradHeart" x1="0" y1="0" x2="1" y2="1">
                          <stop offset="0%" stop-color="#fff0f6"/><stop offset="100%" stop-color="#fda4af"/></linearGradient></defs>
                        <path d="M100 170 C 20 110, 20 40, 60 40 C 80 40, 100 60, 100 80
                                 C 100 60, 120 40, 140 40 C 180 40, 180 110, 100 170 Z"
                              fill="url(#gradHeart)" stroke="#f43f5e" stroke-width="3"/>
                        <text x="100" y="105" text-anchor="middle" dominant-baseline="middle"
                              font-size="56" font-weight="900" fill="#be185d">{num_str}</text>
                      </svg>
                    </div>"""
                    last_digit = int(num_str[-1]) % 10
                else:
                    final_svg, last_digit = "", 0

                return (
                    2,
                    gr.update(visible=False), gr.update(visible=True), gr.update(visible=False),
                    gr.update(value=viz_html),
                    viz_html, final_svg, last_digit,
                    gr.update(value=""), gr.update(value=""),
                    gr.update(visible=True), gr.update(visible=True), gr.update(visible=False)
                )

            # 2 -> 3
            if cur_step == 2:
                m = re.findall(r'>(\d{2})<', f_svg or "")
                score_str = m[0] if m else "--"
                grade, text = fortune_from_last_digit(int(last_d))

                combined = f"""
                <div class="result-wrap">
                  <div class="result-card">
                    {f_svg}
                    <div class="score-chip">점수 {score_str} · 등급 {grade}</div>
                    <div class="desc-box">{text}</div>
                  </div>
                </div>"""

                return (
                    3,
                    gr.update(visible=False), gr.update(visible=False), gr.update(visible=True),
                    gr.update(value=v_html),
                    v_html, f_svg, last_d,
                    gr.update(value=""),                # 단독 하트 영역 비움
                    gr.update(value=combined),          # 카드 렌더
                    gr.update(visible=True), gr.update(visible=False), gr.update(visible=True)
                )

            # 3에서 Next 유지
            return (
                3,
                gr.update(visible=False), gr.update(visible=False), gr.update(visible=True),
                gr.update(value=v_html),
                v_html, f_svg, last_d,
                gr.update(), gr.update(),
                gr.update(visible=True), gr.update(visible=False), gr.update(visible=True)
            )

        def on_prev(cur_step, v_html, f_svg, last_d):
            if cur_step == 2:
                return (
                    1,
                    gr.update(visible=True), gr.update(visible=False), gr.update(visible=False),
                    gr.update(value=v_html),
                    v_html, f_svg, last_d,
                    gr.update(value=""), gr.update(value=""),
                    gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
                )
            if cur_step == 3:
                return (
                    2,
                    gr.update(visible=False), gr.update(visible=True), gr.update(visible=False),
                    gr.update(value=v_html),
                    v_html, f_svg, last_d,
                    gr.update(value=""), gr.update(value=""),
                    gr.update(visible=True), gr.update(visible=True), gr.update(visible=False)
                )
            return (
                1,
                gr.update(visible=True), gr.update(visible=False), gr.update(visible=False),
                gr.update(value=v_html),
                v_html, f_svg, last_d,
                gr.update(value=""), gr.update(value=""),
                gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
            )

        def on_reset():
            return (
                1,
                gr.update(visible=True), gr.update(visible=False), gr.update(visible=False),
                gr.update(value=""), "", "", 0,
                gr.update(value=""), gr.update(value=""),
                gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
            )

        # 이벤트
        btn_next.click(
            on_next,
            inputs=[step_idx, name1, name2, speed, viz_html_state, final_svg_state, last_digit_state],
            outputs=[step_idx, step1, step2, step3, calc_view, viz_html_state, final_svg_state, last_digit_state,
                     final_heart, fortune_text, btn_prev, btn_next, btn_reset]
        )
        btn_prev.click(
            on_prev,
            inputs=[step_idx, viz_html_state, final_svg_state, last_digit_state],
            outputs=[step_idx, step1, step2, step3, calc_view, viz_html_state, final_svg_state, last_digit_state,
                     final_heart, fortune_text, btn_prev, btn_next, btn_reset]
        )
        btn_reset.click(
            on_reset, inputs=[],
            outputs=[step_idx, step1, step2, step3, calc_view, viz_html_state, final_svg_state, last_digit_state,
                     final_heart, fortune_text, btn_prev, btn_next, btn_reset]
        )

    try: webbrowser.open("http://127.0.0.1:7860")
    except Exception: pass
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)

if __name__ == "__main__":
    launch()
