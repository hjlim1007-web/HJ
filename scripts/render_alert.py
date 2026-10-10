"""due.py 출력을 마감 알림 HTML 메일로 조판한다.

    python3 scripts/due.py --date 2026-11-10 | python3 scripts/render_alert.py > out.html
    python3 scripts/render_alert.py --date 2026-11-10 -o out.html

조판을 매일 다시 만들지 않고 스크립트로 고정한다. 알림의 가치는 정확성이므로 날마다
결과가 흔들리지 않는 것이 중요하다. 사양은 routines/email-style.md를 따른다.

표준 출력은 HTML, 표준 오류에 제목 한 줄(`SUBJECT: ...`)을 낸다. 보낼 항목이 없으면
HTML을 내지 않고 종료 코드 3으로 끝낸다 — 그 날은 메일을 보내지 않는다는 신호다.
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WD = "월화수목금토일"

# routines/email-style.md
C_TITLE = "#212529"
C_BODY = "#3a3f44"
C_MUTED = "#8a8f94"
C_HAIR = "#e3e3e3"
C_RULE = "#c9c9c9"
C_ACCENT = "#01c1d6"
C_STRONG = "#150f96"
C_BAND = "#f7f7f7"
FONT = (
    "-apple-system, BlinkMacSystemFont, 'Malgun Gothic', "
    "'Apple SD Gothic Neo', '맑은 고딕', sans-serif"
)


def fmt_date(iso: str) -> str:
    d = datetime.date.fromisoformat(iso)
    return f"{d.isoformat()}({WD[d.weekday()]})"


def esc(text: str | None) -> str:
    if not text:
        return ""
    # yaml 블록 스칼라의 줄바꿈은 한 칸으로 눌러 읽기 흐름을 유지한다.
    return html.escape(" ".join(text.split()))


def subject(payload: dict) -> str:
    alerts = payload["alerts"]
    ref = fmt_date(payload["reference_date"])
    # 가장 급한 항목의 D-n을 제목에 세운다. soonest는 최소값이므로 당일 건이 있으면
    # 반드시 D-0으로 나타난다 — 별도의 "D-0 포함" 표기는 중복이다.
    soonest = min(a["days_until"] for a in alerts)
    return f"[마감] {ref} D-{soonest} 항목 {len(alerts)}건"


def render_item(a: dict) -> str:
    accent = C_STRONG if a["days_until"] == 0 else None
    pad_left = "13px" if accent else "0"
    border = f"border-left:3px solid {accent};" if accent else ""

    head = f"D-{a['days_until']} · {fmt_date(a['due_date'])}"
    tag = (
        f'<span style="font-size:13px;color:{C_ACCENT};"> 미검증</span>'
        if not a["verified"]
        else ""
    )
    shift = (
        f'<span style="font-size:13px;color:{C_MUTED};">'
        f"（원래 {fmt_date(a['raw_due_date'])}, 휴일 보정）</span>"
        if a["shifted"]
        else ""
    )

    rows = [
        f'<div style="font-size:19px;font-weight:600;color:{C_TITLE};'
        f'line-height:1.5;">{esc(a["name"])}{tag}</div>',
        f'<div style="font-size:16px;color:{C_ACCENT};padding-top:4px;">'
        f"{head}{shift}</div>",
    ]
    if a.get("basis"):
        rows.append(
            f'<div style="font-size:16px;color:{C_BODY};line-height:1.7;'
            f'padding-top:10px;">{esc(a["basis"])}</div>'
        )
    if a.get("note"):
        rows.append(
            f'<div style="background:{C_BAND};padding:12px 14px;margin-top:12px;">'
            f'<div style="font-size:13px;color:{C_ACCENT};padding-bottom:4px;">참고</div>'
            f'<div style="font-size:16px;color:{C_BODY};line-height:1.7;">'
            f'{esc(a["note"])}</div></div>'
        )
    if a.get("source"):
        url = html.escape(a["source"], quote=True)
        rows.append(
            f'<div style="font-size:14px;line-height:2;padding-top:8px;">'
            f'<a href="{url}" style="color:{C_ACCENT};text-decoration:none;">출처</a></div>'
        )

    return (
        f'<tr><td style="padding:22px 0;border-bottom:1px solid {C_HAIR};'
        f'{border}padding-left:{pad_left};">' + "".join(rows) + "</td></tr>"
    )


def render(payload: dict) -> str:
    alerts = payload["alerts"]
    cal = payload["calendar"]
    ref = datetime.date.fromisoformat(payload["reference_date"])

    groups: dict[str, list[dict]] = {}
    for a in alerts:
        groups.setdefault(a["category"], []).append(a)
    show_headings = len(groups) > 1

    body: list[str] = []
    for i, (category, items) in enumerate(groups.items()):
        if show_headings:
            top = "28px" if i else "4px"
            body.append(
                f'<tr><td style="padding:{top} 0 0;border-top:1px solid {C_RULE};">'
                f'<div style="font-size:19px;font-weight:600;color:{C_TITLE};'
                f'padding-top:18px;">{esc(category)}</div></td></tr>'
            )
        body.extend(render_item(a) for a in items)

    notes = [
        f"기준일 {fmt_date(ref.isoformat())} · 산출 scripts/due.py",
        "기한일이 휴일이면 보정한 날짜로 D-n을 센다.",
    ]
    if any(not a["verified"] for a in alerts):
        notes.append(
            "미검증 항목은 1차 출처로 확인되지 않은 기한이다 — 실제 기한을 확인하고 쓸 것."
        )
    if cal["years"] and max(cal["years"]) <= ref.year:
        notes.append(
            "공휴일 대장에 다음 해가 없다 — data/holidays.yaml 갱신 필요."
        )
    footnote = "<br>".join(esc(n) for n in notes)

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>마감 알림</title></head>
<body style="margin:0;padding:0;background:#ffffff;">
<table width="100%" cellpadding="0" cellspacing="0" border="0"
  style="background:#ffffff;"><tr><td align="center">
<table width="100%" cellpadding="0" cellspacing="0" border="0"
  style="max-width:680px;font-family:{FONT};word-break:keep-all;">
  <tr><td style="background:{C_TITLE};height:6px;line-height:6px;font-size:0;">&nbsp;</td></tr>
  <tr><td style="padding:30px 24px 0;">
    <div style="font-size:28px;font-weight:600;color:{C_TITLE};">마감 알림</div>
    <div style="font-size:14px;color:{C_MUTED};line-height:1.7;padding-top:10px;">
      {fmt_date(ref.isoformat())}<br>항목 {len(alerts)}건
    </div>
  </td></tr>
  <tr><td style="padding:24px 24px 0;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">{''.join(body)}</table>
  </td></tr>
  <tr><td style="padding:20px 24px 36px;">
    <div style="border-top:1px solid {C_RULE};padding-top:14px;
      font-size:14px;color:{C_MUTED};line-height:1.7;">{footnote}</div>
  </td></tr>
</table></td></tr></table>
</body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="마감 알림 HTML 조판")
    ap.add_argument("--date", help="직접 due.py를 호출할 기준일 YYYY-MM-DD")
    ap.add_argument("-o", "--out", help="출력 파일 (기본: 표준 출력)")
    args = ap.parse_args()

    if args.date:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "due.py"), "--date", args.date],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(proc.stdout)
    else:
        if sys.stdin.isatty():
            ap.error("--date를 주거나 due.py 출력을 표준 입력으로 넘겨라")
        payload = json.load(sys.stdin)

    if not payload.get("alerts"):
        print(
            f"걸린 마감 없음 (기준일 {payload['reference_date']}) — 메일을 보내지 않는다",
            file=sys.stderr,
        )
        return 3

    print(f"SUBJECT: {subject(payload)}", file=sys.stderr)
    out = render(payload)
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"작성: {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
