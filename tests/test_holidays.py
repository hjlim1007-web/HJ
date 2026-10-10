import datetime

import pytest

from holidays import CoverageError, load_calendar

D = datetime.date


@pytest.fixture(scope="module")
def cal():
    return load_calendar()


def test_weekend_is_not_business_day(cal):
    assert not cal.is_business_day(D(2026, 10, 10))  # 토
    assert not cal.is_business_day(D(2026, 10, 11))  # 일
    assert cal.is_business_day(D(2026, 10, 12))  # 월


def test_fixed_holiday(cal):
    assert not cal.is_business_day(D(2026, 1, 1))  # 신정(목)
    assert not cal.is_business_day(D(2026, 10, 9))  # 한글날(금)


def test_substitute_holiday(cal):
    # 삼일절이 일요일 → 3/2(월) 대체공휴일
    assert not cal.is_business_day(D(2026, 3, 2))
    assert cal.is_business_day(D(2026, 3, 3))


def test_memorial_day_has_no_substitute(cal):
    # 현충일은 대체공휴일 대상이 아니다. 2026-06-06(토) 다음 월요일은 영업일.
    assert not cal.is_business_day(D(2026, 6, 6))
    assert cal.is_business_day(D(2026, 6, 8))


def test_labour_day_scope_differs(cal):
    """근로자의 날은 세법 기한(tax)에서는 휴일, 관공서 기준(govt)에서는 영업일."""
    labour = D(2026, 5, 1)
    assert not cal.is_business_day(labour, scope="tax")
    assert not cal.is_business_day(labour, scope="finance")
    assert cal.is_business_day(labour, scope="govt")


def test_lunar_new_year_run(cal):
    for day in (16, 17, 18):
        assert not cal.is_business_day(D(2026, 2, day))
    assert cal.is_business_day(D(2026, 2, 19))


def test_shift_next_business_day_over_long_weekend(cal):
    # 2026-10-09 한글날(금) → 10, 11 주말 → 10-12(월)
    assert cal.shift_to_business_day(D(2026, 10, 9)) == D(2026, 10, 12)


def test_shift_compounds_weekend_and_holiday(cal):
    # 2027-02-28(일) → 03-01 삼일절(월) → 03-02(화)
    assert cal.shift_to_business_day(D(2027, 2, 28)) == D(2027, 3, 2)


def test_shift_previous_business_day(cal):
    assert (
        cal.shift_to_business_day(D(2026, 10, 10), "previous_business_day")
        == D(2026, 10, 8)
    )


def test_shift_none_returns_same_day(cal):
    assert cal.shift_to_business_day(D(2026, 10, 10), "none") == D(2026, 10, 10)


def test_shift_keeps_business_day_unchanged(cal):
    assert cal.shift_to_business_day(D(2026, 10, 13)) == D(2026, 10, 13)


def test_business_days_between(cal):
    # 10-09(금, 한글날) 다음부터 10-13(화)까지: 10-12, 10-13 두 영업일
    assert cal.business_days_between(D(2026, 10, 9), D(2026, 10, 13)) == 2
    assert cal.business_days_between(D(2026, 10, 13), D(2026, 10, 13)) == 0
    # 역방향: 10-12(o), 10-11·10-10 주말, 10-09 한글날, 10-08(o) → 2영업일
    assert cal.business_days_between(D(2026, 10, 13), D(2026, 10, 8)) == -2
    # end가 휴일이면 세지 않는다 — 10-12 하나뿐
    assert cal.business_days_between(D(2026, 10, 13), D(2026, 10, 9)) == -1


def test_year_outside_coverage_raises(cal):
    """대장 밖 연도를 조용히 '전부 영업일'로 답하면 기한을 틀린다."""
    with pytest.raises(CoverageError):
        cal.is_business_day(D(2028, 3, 2))
    with pytest.raises(CoverageError):
        cal.is_business_day(D(2025, 3, 2))


def test_invalid_scope_and_rule(cal):
    with pytest.raises(ValueError):
        cal.is_business_day(D(2026, 10, 12), scope="없는scope")
    with pytest.raises(ValueError):
        cal.shift_to_business_day(D(2026, 10, 12), "없는rule")


def test_holiday_metadata(cal):
    [h] = cal.holidays_on(D(2026, 7, 17))
    assert h.name == "제헌절"
    assert h.confidence in {"high", "medium"}
