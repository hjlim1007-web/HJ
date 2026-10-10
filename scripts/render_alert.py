"""due.py 출력을 마감 알림 HTML 메일로 조판한다.

    python3 scripts/due.py --date 2026-11-10 | python3 scripts/render_alert.py > out.html
    python3 scripts/render_alert.py --date 2026-11-10 -o out.html

조판을 매일 다시 만들지 않고 스크립트로 고정한다. 알림의 가치는 정확성이므로 날마다
결과가 흔들리지 않는 것이 중요하다. 색·서체·페이지 틀은 mailstyle.py에 있다.

표준 출력은 HTML, 표준 오류에 제목 한 줄(`SUBJECT: ...`)을 낸다. 보낼 항목이 없으면
HTML을 내지 않고 종료 코드 3으로 끝낸다 — 그 날은 메일을 보내지 않는다는 신호다.
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

from mailstyle import (
    C_ACCENT,
    C_BAND,
    C_BODY,
    C_HAIR,
    C_MUTED,
    C_STRONG,
    C_TITLE,
    SIZE_BODY,
    SIZE_SECTION,
    SIZE_SMALL,
    esc,
    fmt_date,
    link,
    page,
    section_head,
)

ROOT = Path(__file__).resolve().parent


def subject(payload: dict) -> str:
    alerts = payload["alerts"]
    ref = fmt_date(payload["reference_date"])
    # 가장 급한 항목의 D-n을 제목에 세운다. soonest는 최소값이므로 당일 건이 있으면
    # 반드시 D-0으로 나타난다 — 별도의 "D-0 포함" 표기는 중복이다.
    soonest = min(a["days_until"] for a in alerts)
    return f"[마감] {ref} D-{soonest} 항목 {len(alerts)}건"


def render_item(a: dict) -> str:
    # D-0 항목만 왼쪽에 진한 파랑 세로선을 둔다 — 지면에서 가장 급한 것 하나만 세운다.
    urgent = a["days_until"] == 0
    border = f"border-left:3px solid {C_STRONG};padding-left:13px;" if urgent else ""

    tag = (
        f'<span style="font-size:{SIZE_SMALL}px;color:{C_ACCENT};"> 미검증</span>'
        if not a["verified"]
        else ""
    )
    shift = (
        f'<span style="font-size:{SIZE_SMALL}px;color:{C_MUTED};">'
        f"（원래 {fmt_date(a['raw_due_date'])}, 휴일 보정）</span>"
        if a["shifted"]
        else ""
    )

    rows = [
        f'<div style="font-size:{SIZE_SECTION}px;font-weight:600;color:{C_TITLE};'
        f'line-height:1.5;">{esc(a["name"])}{tag}</div>',
        f'<div style="font-size:{SIZE_BODY}px;color:{C_ACCENT};padding-top:4px;">'
        f"D-{a['days_until']} · {fmt_date(a['due_date'])}{shift}</div>",
    ]
    if a.get("basis"):
        rows.append(
            f'<div style="font-size:{SIZE_BODY}px;color:{C_BODY};line-height:1.7;'
            f'padding-top:10px;">{esc(a["basis"])}</div>'
        )
    if a.get("note"):
        rows.append(
            f'<div style="background:{C_BAND};padding:12px 14px;margin-top:12px;">'
            f'<div style="font-size:{SIZE_SMALL}px;color:{C_ACCENT};'
            f'padding-bottom:4px;">참고</div>'
            f'<div style="font-size:{SIZE_BODY}px;color:{C_BODY};line-height:1.7;">'
            f'{esc(a["note"])}</div></div>'
        )
    if a.get("source"):
        rows.append(
            f'<div style="font-size:14px;line-height:2;padding-top:8px;">'
            f'{link(a["source"], "출처")}</div>'
        )

    return (
        f'<tr><td style="padding:22px 0;border-bottom:1px solid {C_HAIR};{border}">'
        + "".join(rows)
        + "</td></tr>"
    )


def render(payload: dict) -> str:
    alerts = payload["alerts"]
    cal = payload["calendar"]
    ref = datetime.date.fromisoformat(payload["reference_date"])

    groups: dict[str, list[dict]] = {}
    for a in alerts:
        groups.setdefault(a["category"], []).append(a)

    body: list[str] = []
    for i, (category, items) in enumerate(groups.items()):
        # 분류가 1종이면 소제목을 넣지 않는다 — 전부 같은 분류인데 머리를 다는 건 군더더기다.
        if len(groups) > 1:
            body.append(section_head(None, category, first=(i == 0)))
        body.extend(render_item(a) for a in items)

    footnotes = [
        f"기준일 {fmt_date(ref)} · 산출 scripts/due.py",
        "기한일이 휴일이면 보정한 날짜로 D-n을 센다.",
    ]
    if any(not a["verified"] for a in alerts):
        footnotes.append(
            "미검증 항목은 1차 출처로 확인되지 않은 기한이다 — 실제 기한을 확인하고 쓸 것."
        )
    if cal["years"] and max(cal["years"]) <= ref.year:
        footnotes.append("공휴일 대장에 다음 해가 없다 — data/holidays.yaml 갱신 필요.")

    return page(
        title="마감 알림",
        header_lines=[fmt_date(ref), f"항목 {len(alerts)}건"],
        body="".join(body),
        footnotes=footnotes,
    )


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
