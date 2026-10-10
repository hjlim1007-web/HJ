"""공휴일 로드와 영업일 보정.

네트워크를 타지 않는다. `data/holidays.yaml`만 읽는다.

scope — 어느 휴일 집합을 쉬는 날로 볼 것인가
  tax     국세기본법 제5조(기한의 특례). 공휴일·토요일·근로자의 날의 다음 날을 기한으로 한다.
  finance 금융기관 휴무 기준. 근로자의 날에 금융기관이 쉬므로 tax와 같은 집합이다.
  govt    관공서 공휴일 기준. 근로자의 날에 관공서는 근무하므로 제외한다.

커버리지 밖 날짜를 물으면 CoverageError를 낸다. 공휴일 정보가 없는 연도를 조용히
'전부 영업일'로 답하면 기한을 틀리게 계산하므로, 침묵보다 실패가 낫다.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "holidays.yaml"

SCOPE_TYPES: dict[str, frozenset[str]] = {
    "tax": frozenset({"공휴일", "대체공휴일", "근로자의날", "선거일", "임시공휴일"}),
    "finance": frozenset({"공휴일", "대체공휴일", "근로자의날", "선거일", "임시공휴일"}),
    "govt": frozenset({"공휴일", "대체공휴일", "선거일", "임시공휴일"}),
}

HOLIDAY_RULES = ("next_business_day", "previous_business_day", "none")


class CoverageError(Exception):
    """공휴일 대장이 다루지 않는 연도를 조회했다."""


@dataclass(frozen=True)
class Holiday:
    date: datetime.date
    name: str
    type: str
    confidence: str
    note: str | None = None


@dataclass(frozen=True)
class Calendar:
    by_date: dict[datetime.date, list[Holiday]]
    years: frozenset[int]
    updated_on: datetime.date | None
    verified_against_primary_source: bool

    def _check_coverage(self, d: datetime.date) -> None:
        if d.year not in self.years:
            covered = ", ".join(str(y) for y in sorted(self.years))
            raise CoverageError(
                f"{d.isoformat()}는 공휴일 대장 범위 밖이다 (수록 연도: {covered}). "
                "data/holidays.yaml을 갱신한 뒤 다시 실행하라."
            )

    def holidays_on(self, d: datetime.date, scope: str = "tax") -> list[Holiday]:
        """해당 날짜의 휴일 중 scope에 해당하는 것. 없으면 빈 리스트."""
        types = _scope_types(scope)
        self._check_coverage(d)
        return [h for h in self.by_date.get(d, []) if h.type in types]

    def is_business_day(self, d: datetime.date, scope: str = "tax") -> bool:
        self._check_coverage(d)
        if d.weekday() >= 5:  # 토(5)·일(6)
            return False
        return not self.holidays_on(d, scope)

    def shift_to_business_day(
        self, d: datetime.date, rule: str = "next_business_day", scope: str = "tax"
    ) -> datetime.date:
        """기한일이 휴일일 때 보정한 날짜. rule='none'이면 그대로 돌려준다."""
        if rule not in HOLIDAY_RULES:
            raise ValueError(f"holiday_rule은 {HOLIDAY_RULES} 중 하나여야 한다: {rule!r}")
        if rule == "none":
            self._check_coverage(d)
            return d
        step = 1 if rule == "next_business_day" else -1
        cur = d
        for _ in range(40):  # 연휴 최장을 넉넉히 넘기는 상한
            if self.is_business_day(cur, scope):
                return cur
            cur += datetime.timedelta(days=step)
        raise RuntimeError(f"{d.isoformat()} 기준 영업일을 40일 안에 찾지 못했다")

    def business_days_between(
        self, start: datetime.date, end: datetime.date, scope: str = "tax"
    ) -> int:
        """start를 뺀 start~end 구간의 영업일 수. end가 start보다 앞이면 음수.

        순방향은 (start, end] 구간, 역방향은 [end, start) 구간을 센다. 어느 쪽이든
        start는 세지 않고 end는 센다 — end가 휴일이면 그만큼 적게 나온다.
        """
        if end == start:
            return 0
        step = 1 if end > start else -1
        count = 0
        cur = start
        while cur != end:
            cur += datetime.timedelta(days=step)
            if self.is_business_day(cur, scope):
                count += step
        return count


def _scope_types(scope: str) -> frozenset[str]:
    try:
        return SCOPE_TYPES[scope]
    except KeyError:
        raise ValueError(
            f"scope는 {tuple(SCOPE_TYPES)} 중 하나여야 한다: {scope!r}"
        ) from None


def load_calendar(path: Path | str = DEFAULT_PATH) -> Calendar:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    meta = raw.get("meta") or {}
    by_date: dict[datetime.date, list[Holiday]] = {}
    years: set[int] = set()

    for item in raw.get("holidays") or []:
        d = item["date"]
        if not isinstance(d, datetime.date):
            d = datetime.date.fromisoformat(str(d))
        if item["type"] not in set().union(*SCOPE_TYPES.values()):
            raise ValueError(f"알 수 없는 휴일 type: {item['type']!r} ({d})")
        by_date.setdefault(d, []).append(
            Holiday(
                date=d,
                name=item["name"],
                type=item["type"],
                confidence=item.get("confidence", "medium"),
                note=item.get("note"),
            )
        )
        years.add(d.year)

    if not years:
        raise ValueError(f"{path}에 공휴일 항목이 없다")

    # 수록 연도 사이에 빈 해가 있으면 그 해를 '휴일 없음'으로 오답하게 되므로 막는다.
    lo, hi = min(years), max(years)
    missing = [y for y in range(lo, hi + 1) if y not in years]
    if missing:
        raise ValueError(
            f"공휴일 대장에 빠진 연도가 있다: {missing}. 연속된 연도만 수록해야 한다."
        )

    updated = meta.get("updated_on")
    if updated is not None and not isinstance(updated, datetime.date):
        updated = datetime.date.fromisoformat(str(updated))

    return Calendar(
        by_date=by_date,
        years=frozenset(years),
        updated_on=updated,
        verified_against_primary_source=bool(
            meta.get("verified_against_primary_source", False)
        ),
    )


if __name__ == "__main__":
    cal = load_calendar()
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    print(f"수록 연도: {sorted(cal.years)}  갱신일: {cal.updated_on}")
    print(f"1차 출처 검증: {'완료' if cal.verified_against_primary_source else '미완료'}")
    print(f"{today} 영업일(tax): {cal.is_business_day(today)}")
    for h in cal.holidays_on(today):
        print(f"  휴일: {h.name} ({h.type}, confidence={h.confidence})")
