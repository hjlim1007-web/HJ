"""시장지표 한 행을 검증해 series.csv에 추가한다.

    echo '{"date":"2026-10-09","usdkrw":1352.4,"source":"서울외환시장 종가"}' \
      | python3 scripts/market_append.py
    python3 scripts/market_append.py --field date=2026-10-09 --field usdkrw=1352.4 \
      --field source="서울외환시장 종가"
    python3 scripts/market_append.py --dry-run --field ...

검증에 걸리면 **아무것도 쓰지 않고** 사유를 내며 종료 코드 2로 끝낸다. 확인하지 못한
값은 빈 칸으로 둔다 — 0이나 추정치로 메우는 것이 가장 나쁜 실패 양식이다.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

from holidays import load_calendar
from market_series import (
    SERIES_PATH,
    ValidationError,
    append_row,
    existing_dates,
    load_columns,
    validate,
)

KST = datetime.timezone(datetime.timedelta(hours=9))


def main() -> int:
    ap = argparse.ArgumentParser(description="시장지표 한 행 적재")
    ap.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="열 값. 여러 번 줄 수 있다. 표준 입력 JSON과 함께 주면 이쪽이 이긴다",
    )
    ap.add_argument("--csv", default=str(SERIES_PATH), help="대상 CSV")
    ap.add_argument("--dry-run", action="store_true", help="검증만 하고 쓰지 않는다")
    ap.add_argument("--today", help="미래 날짜 판정 기준일 (테스트용)")
    args = ap.parse_args()

    payload: dict = {}
    if not sys.stdin.isatty():
        text = sys.stdin.read().strip()
        if text:
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as e:
                print(f"표준 입력이 JSON이 아니다: {e}", file=sys.stderr)
                return 2
    for item in args.field:
        if "=" not in item:
            print(f"--field는 KEY=VALUE 형식이어야 한다 — {item!r}", file=sys.stderr)
            return 2
        key, _, value = item.partition("=")
        payload[key.strip()] = value

    if not payload:
        print("입력이 없다 — 표준 입력 JSON이나 --field를 줘라", file=sys.stderr)
        return 2

    cols = load_columns()
    cal = load_calendar()
    today = (
        datetime.date.fromisoformat(args.today)
        if args.today
        else datetime.datetime.now(KST).date()
    )

    try:
        row = validate(
            payload,
            cols,
            known_dates=existing_dates(args.csv),
            covered_years=cal.years,
            today=today,
        )
    except ValidationError as e:
        print(f"거부: {e}", file=sys.stderr)
        return 2

    filled = [c.name for c in cols if row[c.name] != ""]
    blank = [c.name for c in cols if row[c.name] == ""]

    if args.dry_run:
        print(f"검증 통과 (쓰지 않음) — {row['date']} 값 {len(filled)}개", file=sys.stderr)
    else:
        append_row(row, cols, args.csv)
        print(f"추가: {row['date']} 값 {len(filled)}개", file=sys.stderr)
    if blank:
        print(f"빈 칸: {', '.join(blank)}", file=sys.stderr)

    json.dump(row, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
