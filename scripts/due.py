"""기준일에 알려야 할 마감 항목만 골라 JSON으로 낸다.

    python3 scripts/due.py                      # 오늘(KST) 기준
    python3 scripts/due.py --date 2026-10-12
    python3 scripts/due.py --all                # 모든 항목의 다음 기한 (점검용)

네트워크를 타지 않는다. data/deadlines.yaml + data/holidays.yaml만 읽는다.

기한일이 휴일이면 holiday_rule로 보정하고, **보정된 날짜**를 기준으로 D-n을 센다.
보정 전 날짜로 알리면 실제 기한과 하루 이틀 어긋나기 때문이다.
"""

from __future__ import annotations

import argparse
import calendar as _calendar
import datetime
import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from holidays import Calendar, load_calendar

ROOT = Path(__file__).resolve().parent.parent
DEADLINES_PATH = ROOT / "data" / "deadlines.yaml"
KST = datetime.timezone(datetime.timedelta(hours=9))


@dataclass(frozen=True)
class Alert:
    id: str
    name: str
    category: str
    due_date: datetime.date
    raw_due_date: datetime.date
    days_until: int
    verified: bool
    basis: str | None
    note: str | None
    source: str | None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "due_date": self.due_date.isoformat(),
            "raw_due_date": self.raw_due_date.isoformat(),
            "shifted": self.due_date != self.raw_due_date,
            "days_until": self.days_until,
            "verified": self.verified,
            "basis": self.basis,
            "note": self.note,
            "source": self.source,
        }


def _resolve_day(year: int, month: int, day: int | str) -> datetime.date:
    last = _calendar.monthrange(year, month)[1]
    if isinstance(day, str):
        if day != "last":
            raise ValueError(f"day는 정수 또는 'last'여야 한다: {day!r}")
        return datetime.date(year, month, last)
    return datetime.date(year, month, min(int(day), last))


def _raw_occurrences(
    rule: dict, start: datetime.date, end: datetime.date
) -> list[datetime.date]:
    """[start, end] 구간에 들어오는 원래 기한일 목록."""
    months = rule.get("months")
    day = rule.get("day", "last")
    out: list[datetime.date] = []
    year, month = start.year, start.month
    while datetime.date(year, month, 1) <= end:
        if months is None or month in months:
            d = _resolve_day(year, month, day)
            if start <= d <= end:
                out.append(d)
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return out


def _as_date(value) -> datetime.date | None:
    if value is None:
        return None
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value))


def build_alerts(
    deadlines: list[dict], cal: Calendar, ref: datetime.date, show_all: bool = False
) -> list[Alert]:
    alerts: list[Alert] = []

    for item in deadlines:
        if not item.get("enabled", True):
            continue

        leads = sorted({int(x) for x in item.get("leads", [0])}, reverse=True)
        horizon = max(leads) if leads else 0
        rule = item.get("recurrence") or {}
        holiday_rule = item.get("holiday_rule", "next_business_day")
        scope = item.get("scope", "tax")
        eff_from = _as_date(item.get("effective_from"))
        eff_until = _as_date(item.get("effective_until"))

        # 보정이 날짜를 양쪽으로 최대 2주 가까이 밀 수 있으므로 구간을 넉넉히 잡는다.
        window_start = ref - datetime.timedelta(days=45)
        window_end = ref + datetime.timedelta(days=horizon + 45)

        seen: set[datetime.date] = set()
        for raw in _raw_occurrences(rule, window_start, window_end):
            if eff_from and raw < eff_from:
                continue
            if eff_until and raw > eff_until:
                continue

            due = cal.shift_to_business_day(raw, holiday_rule, scope)
            if due in seen:
                continue
            seen.add(due)

            days_until = (due - ref).days
            if show_all:
                if days_until < 0:
                    continue
            elif days_until not in leads:
                continue

            alerts.append(
                Alert(
                    id=item["id"],
                    name=item["name"],
                    category=item["category"],
                    due_date=due,
                    raw_due_date=raw,
                    days_until=days_until,
                    verified=bool(item.get("verified", False)),
                    basis=item.get("basis"),
                    note=item.get("note"),
                    source=item.get("source"),
                )
            )

    if show_all:
        # 항목마다 가장 가까운 기한 하나만 남긴다.
        nearest: dict[str, Alert] = {}
        for a in alerts:
            if a.id not in nearest or a.days_until < nearest[a.id].days_until:
                nearest[a.id] = a
        alerts = list(nearest.values())

    alerts.sort(key=lambda a: (a.due_date, a.category, a.id))
    return alerts


def main() -> int:
    parser = argparse.ArgumentParser(description="마감 D-day 알림 대상 산출")
    parser.add_argument("--date", help="기준일 YYYY-MM-DD (기본: 오늘 KST)")
    parser.add_argument(
        "--all", action="store_true", help="leads 무시하고 모든 항목의 다음 기한 출력"
    )
    parser.add_argument("--deadlines", default=str(DEADLINES_PATH))
    args = parser.parse_args()

    ref = (
        datetime.date.fromisoformat(args.date)
        if args.date
        else datetime.datetime.now(KST).date()
    )

    raw = yaml.safe_load(Path(args.deadlines).read_text(encoding="utf-8"))
    cal = load_calendar()
    alerts = build_alerts(raw.get("deadlines") or [], cal, ref, show_all=args.all)

    payload = {
        "reference_date": ref.isoformat(),
        "mode": "all" if args.all else "due",
        "calendar": {
            "years": sorted(cal.years),
            "updated_on": cal.updated_on.isoformat() if cal.updated_on else None,
            "verified_against_primary_source": cal.verified_against_primary_source,
        },
        "alert_count": len(alerts),
        "unverified_count": sum(1 for a in alerts if not a.verified),
        "alerts": [a.to_dict() for a in alerts],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
