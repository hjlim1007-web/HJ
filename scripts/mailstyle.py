"""HTML 메일 조판 공통부.

`routines/email-style.md`를 구현한다. 마감 알림과 월간 리뷰가 같은 지면을 쓰도록
색·서체·페이지 틀을 한 곳에 둔다. 사양을 바꾸려면 이 파일을 고치고 테스트를 돌린다.

수신자는 아이폰 메일로 읽는다. 고정폭 table을 쓰면 메일 앱이 지면 전체를 축소해 띄워
글자가 읽을 수 없게 작아지므로, 바깥은 width="100%", 본문은 max-width로만 묶는다.
"""

from __future__ import annotations

import datetime
import html

WD = "월화수목금토일"
KST = datetime.timezone(datetime.timedelta(hours=9))

# routines/email-style.md 의 색
C_TITLE = "#212529"
C_BODY = "#3a3f44"
C_MUTED = "#8a8f94"
C_HAIR = "#e3e3e3"
C_RULE = "#c9c9c9"
C_ACCENT = "#01c1d6"
C_STRONG = "#150f96"
C_BAND = "#f7f7f7"
C_DOWN = "#0e7c86"

# 세리프를 쓰지 않는다 — 수신자가 바탕체 렌더링을 싫어한다
FONT = (
    "-apple-system, BlinkMacSystemFont, 'Malgun Gothic', "
    "'Apple SD Gothic Neo', '맑은 고딕', sans-serif"
)

# 글자 크기 4종만. 본문은 16px 아래로 내리지 않는다.
SIZE_TITLE = 28
SIZE_SECTION = 19
SIZE_BODY = 16
SIZE_LABEL = 14
SIZE_SMALL = 13


def today_kst() -> datetime.date:
    return datetime.datetime.now(KST).date()


def fmt_date(value: str | datetime.date) -> str:
    """2026-11-10 → '2026-11-10(화)'"""
    d = value if isinstance(value, datetime.date) else datetime.date.fromisoformat(value)
    return f"{d.isoformat()}({WD[d.weekday()]})"


def esc(text: str | None) -> str:
    """HTML 이스케이프. yaml 블록 스칼라의 줄바꿈은 한 칸으로 눌러 읽기 흐름을 유지한다."""
    if not text:
        return ""
    return html.escape(" ".join(str(text).split()))


def link(url: str, label: str) -> str:
    return (
        f'<a href="{html.escape(url, quote=True)}" '
        f'style="color:{C_ACCENT};text-decoration:none;">{esc(label)}</a>'
    )


def delta_mark(value: float | None, digits: int = 2) -> str:
    """전일·전월 대비 변동 표기. 상승 ▲ 진한 파랑, 하락 ▼ 진한 청록."""
    if value is None:
        return f'<span style="color:{C_MUTED};">—</span>'
    if value > 0:
        return f'<span style="color:{C_STRONG};">▲ {value:+,.{digits}f}</span>'
    if value < 0:
        return f'<span style="color:{C_DOWN};">▼ {value:+,.{digits}f}</span>'
    return f'<span style="color:{C_MUTED};">0.00</span>'


def kv_rows(pairs: list[tuple[str, str, str | None]]) -> str:
    """2열 표의 행들. (항목명, 값, 비고) — 3열 표는 375px에서 읽히지 않으므로 쓰지 않는다.

    항목명 아래에 비고를 13px로 붙이고, 값은 우측 정렬 + nowrap으로 줄바꿈을 막는다.
    """
    out = []
    for name, value, note in pairs:
        sub = (
            f'<div style="font-size:{SIZE_SMALL}px;color:{C_MUTED};padding-top:2px;">'
            f"{esc(note)}</div>"
            if note
            else ""
        )
        out.append(
            f'<tr><td style="padding:11px 0;border-bottom:1px solid {C_HAIR};'
            f'font-size:{SIZE_BODY}px;color:{C_BODY};">{esc(name)}{sub}</td>'
            f'<td align="right" style="padding:11px 0;border-bottom:1px solid {C_HAIR};'
            f'font-size:{SIZE_BODY}px;color:{C_TITLE};white-space:nowrap;">{value}</td></tr>'
        )
    return "".join(out)


def table(inner: str) -> str:
    """격자 테두리 없는 2열 표. 행 아래 머리카락 선만 둔다."""
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0">{inner}</table>'
    )


def section_head(number: str | None, name: str, first: bool = False) -> str:
    """위에 구분선 + 청록 번호 + 섹션명."""
    top = "4px" if first else "28px"
    num = (
        f'<span style="color:{C_ACCENT};">{esc(number)}</span> ' if number else ""
    )
    return (
        f'<tr><td style="padding:{top} 0 0;border-top:1px solid {C_RULE};">'
        f'<div style="font-size:{SIZE_SECTION}px;font-weight:600;color:{C_TITLE};'
        f'padding-top:18px;">{num}{esc(name)}</div></td></tr>'
    )


def page(*, title: str, header_lines: list[str], body: str, footnotes: list[str]) -> str:
    """메일 한 통의 전체 지면.

    title        28px 머리말
    header_lines 머리말 아래 14px 보조색, <br>로 끊는다
    body         <tr> 들의 연결 (table()로 감싸기 전 상태)
    footnotes    맨 아래 구분선 아래 14px 보조색
    """
    head = "<br>".join(esc(x) for x in header_lines)
    foot = "<br>".join(esc(x) for x in footnotes)
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title></head>
<body style="margin:0;padding:0;background:#ffffff;">
<table width="100%" cellpadding="0" cellspacing="0" border="0"
  style="background:#ffffff;"><tr><td align="center">
<table width="100%" cellpadding="0" cellspacing="0" border="0"
  style="max-width:680px;font-family:{FONT};word-break:keep-all;">
  <tr><td style="background:{C_TITLE};height:6px;line-height:6px;font-size:0;">&nbsp;</td></tr>
  <tr><td style="padding:30px 24px 0;">
    <div style="font-size:{SIZE_TITLE}px;font-weight:600;color:{C_TITLE};">{esc(title)}</div>
    <div style="font-size:{SIZE_LABEL}px;color:{C_MUTED};line-height:1.7;padding-top:10px;">
      {head}
    </div>
  </td></tr>
  <tr><td style="padding:24px 24px 0;">{table(body)}</td></tr>
  <tr><td style="padding:20px 24px 36px;">
    <div style="border-top:1px solid {C_RULE};padding-top:14px;
      font-size:{SIZE_LABEL}px;color:{C_MUTED};line-height:1.7;">{foot}</div>
  </td></tr>
</table></td></tr></table>
</body></html>
"""
