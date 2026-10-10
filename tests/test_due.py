import datetime

import pytest
import yaml

from due import build_alerts
from holidays import load_calendar

D = datetime.date


@pytest.fixture(scope="module")
def cal():
    return load_calendar()


@pytest.fixture(scope="module")
def deadlines():
    return yaml.safe_load(open("data/deadlines.yaml", encoding="utf-8"))["deadlines"]


def ids_on(items, cal, ref, show_all=False):
    return {a.id: a for a in build_alerts(items, cal, ref, show_all=show_all)}


def only(items, deadline_id):
    return [i for i in items if i["id"] == deadline_id]


# --------------------------- 기본 동작 ---------------------------

def test_withholding_tax_shifts_over_weekend(cal, deadlines):
    """원천세 기한 10일이 토요일이면 다음 영업일로 밀린다."""
    wht = only(deadlines, "wht-monthly")
    # 2026-10-10(토), 10-11(일) → 10-12(월)
    got = ids_on(wht, cal, D(2026, 10, 12))
    assert got["wht-monthly"].due_date == D(2026, 10, 12)
    assert got["wht-monthly"].raw_due_date == D(2026, 10, 10)
    assert got["wht-monthly"].days_until == 0


def test_withholding_tax_on_plain_month(cal, deadlines):
    """2026-11-10은 화요일이므로 보정이 없다."""
    wht = only(deadlines, "wht-monthly")
    got = ids_on(wht, cal, D(2026, 11, 10))
    assert got["wht-monthly"].due_date == D(2026, 11, 10)
    assert got["wht-monthly"].raw_due_date == D(2026, 11, 10)


def test_lead_days_trigger_exactly(cal, deadlines):
    """leads에 든 날에만 걸리고 그 밖의 날에는 걸리지 않는다."""
    wht = only(deadlines, "wht-monthly")  # leads: [7, 3, 1, 0]
    due = D(2026, 11, 10)
    for lead in (7, 3, 1, 0):
        ref = due - datetime.timedelta(days=lead)
        assert "wht-monthly" in ids_on(wht, cal, ref), f"D-{lead}에 걸려야 한다"
    for lead in (8, 6, 4, 2):
        ref = due - datetime.timedelta(days=lead)
        assert "wht-monthly" not in ids_on(wht, cal, ref), f"D-{lead}에 걸리면 안 된다"


def test_past_deadline_does_not_alert(cal, deadlines):
    wht = only(deadlines, "wht-monthly")
    assert "wht-monthly" not in ids_on(wht, cal, D(2026, 10, 13))


def test_quiet_day_has_no_alerts(cal, deadlines):
    """해당 항목이 없는 날에는 빈 결과가 나와야 한다 — 그 날은 메일이 가지 않는다."""
    assert build_alerts(deadlines, cal, D(2026, 10, 14)) == []


# ------------------------- 휴일 보정 경계 -------------------------

def test_lunar_new_year_pushes_month_end(cal, deadlines):
    """2026-02-28(토) 말일 기한 → 3/2 대체공휴일 → 3/3(화)."""
    item = only(deadlines, "simple-stmt-business-other")
    got = ids_on(item, cal, D(2026, 3, 3))
    assert got["simple-stmt-business-other"].raw_due_date == D(2026, 2, 28)
    assert got["simple-stmt-business-other"].due_date == D(2026, 3, 3)


def test_feb_end_compounds_into_march_first(cal, deadlines):
    """2027-02-28(일) → 03-01 삼일절(월) → 03-02(화). 금융소득 지급명세서."""
    item = only(deadlines, "pay-stmt-annual-financial")
    got = ids_on(item, cal, D(2027, 3, 2))
    assert got["pay-stmt-annual-financial"].raw_due_date == D(2027, 2, 28)
    assert got["pay-stmt-annual-financial"].due_date == D(2027, 3, 2)


def test_labour_day_counts_for_tax_scope(cal, deadlines):
    """세법 기한은 근로자의 날에도 밀린다 (국세기본법 제5조)."""
    item = [
        {
            "id": "probe",
            "name": "probe",
            "category": "세무",
            "recurrence": {"months": [5], "day": 1},
            "holiday_rule": "next_business_day",
            "scope": "tax",
            "leads": [0],
        }
    ]
    got = ids_on(item, cal, D(2026, 5, 4))
    assert got["probe"].raw_due_date == D(2026, 5, 1)
    assert got["probe"].due_date == D(2026, 5, 4)  # 5/1 금 근로자의 날 → 주말 → 5/4 월


def test_govt_scope_ignores_labour_day(cal, deadlines):
    item = [
        {
            "id": "probe",
            "name": "probe",
            "category": "감독보고",
            "recurrence": {"months": [5], "day": 1},
            "holiday_rule": "next_business_day",
            "scope": "govt",
            "leads": [0],
        }
    ]
    got = ids_on(item, cal, D(2026, 5, 1))
    assert got["probe"].due_date == D(2026, 5, 1)


def test_holiday_rule_none_keeps_weekend_date(cal, deadlines):
    """업무보고서는 보정 방향을 확인하지 못해 none이다 — 2026-10-31(토) 그대로."""
    item = only(deadlines, "fss-monthly-report")
    got = ids_on(item, cal, D(2026, 10, 31))
    assert got["fss-monthly-report"].due_date == D(2026, 10, 31)


def test_previous_business_day_rule(cal):
    item = [
        {
            "id": "probe",
            "name": "probe",
            "category": "결산",
            "recurrence": {"months": [10], "day": "last"},
            "holiday_rule": "previous_business_day",
            "scope": "govt",
            "leads": [0],
        }
    ]
    # 2026-10-31(토) → 직전 영업일 10-30(금)
    got = ids_on(item, cal, D(2026, 10, 30))
    assert got["probe"].due_date == D(2026, 10, 30)


# --------------------------- 규칙 변경 ---------------------------

def test_wage_statement_handover_has_no_gap_or_overlap(cal, deadlines):
    """근로소득 간이지급명세서 반기 → 매월 승계가 끊기거나 겹치지 않아야 한다."""
    items = [
        i for i in deadlines if i["id"].startswith("simple-stmt-wage")
    ]
    semi = ids_on(items, cal, D(2027, 1, 1), show_all=True)
    assert set(semi) == {"simple-stmt-wage-semiannual"}
    assert semi["simple-stmt-wage-semiannual"].due_date == D(2027, 2, 1)

    after = ids_on(items, cal, D(2027, 3, 1), show_all=True)
    assert set(after) == {"simple-stmt-wage-monthly"}
    assert after["simple-stmt-wage-monthly"].due_date == D(2027, 3, 2)


def test_effective_from_excludes_earlier_occurrences(cal, deadlines):
    monthly = only(deadlines, "simple-stmt-wage-monthly")
    # effective_from 2027-02-01 이므로 2026년 기한은 생성되지 않는다
    assert build_alerts(monthly, cal, D(2026, 11, 30), show_all=True) == []


# --------------------------- 기타 ---------------------------

def test_disabled_items_are_skipped(cal, deadlines):
    disabled = {i["id"] for i in deadlines if not i.get("enabled", True)}
    assert disabled, "enabled:false 항목이 있어야 이 테스트가 의미를 가진다"
    produced = {a.id for a in build_alerts(deadlines, cal, D(2026, 11, 30), show_all=True)}
    assert not (produced & disabled)


def test_all_mode_returns_one_nearest_per_item(cal, deadlines):
    alerts = build_alerts(deadlines, cal, D(2026, 10, 10), show_all=True)
    ids = [a.id for a in alerts]
    assert len(ids) == len(set(ids))
    assert all(a.days_until >= 0 for a in alerts)


def test_alerts_sorted_by_due_date(cal, deadlines):
    alerts = build_alerts(deadlines, cal, D(2026, 10, 10), show_all=True)
    assert alerts == sorted(alerts, key=lambda a: (a.due_date, a.category, a.id))


def test_unverified_items_are_flagged(cal, deadlines):
    """미검증 항목은 verified=False로 나가 메일에 「미검증」 표시가 붙는다."""
    alerts = build_alerts(deadlines, cal, D(2026, 10, 12))
    assert alerts
    assert all(a.verified is False for a in alerts)


def test_day_clamps_to_month_end(cal):
    item = [
        {
            "id": "probe",
            "name": "probe",
            "category": "세무",
            "recurrence": {"months": [2], "day": 31},
            "holiday_rule": "none",
            "scope": "tax",
            "leads": [0],
        }
    ]
    got = ids_on(item, cal, D(2026, 2, 28))
    assert got["probe"].due_date == D(2026, 2, 28)


def test_verified_items_must_carry_a_source(deadlines):
    """기억으로 쓴 날짜가 검증된 것처럼 올라가는 경로를 막는다."""
    bad = [
        i["id"]
        for i in deadlines
        if i.get("verified") and not str(i.get("source") or "").strip()
    ]
    assert not bad, f"verified: true 인데 source가 없다: {bad}"


def test_every_deadline_states_its_basis(deadlines):
    missing = [i["id"] for i in deadlines if not str(i.get("basis") or "").strip()]
    assert not missing, f"basis가 없는 항목: {missing}"
