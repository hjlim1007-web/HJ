import datetime

import pytest

from market_series import (
    ValidationError,
    append_row,
    existing_dates,
    header,
    load_columns,
    read_rows,
    validate,
)

D = datetime.date
TODAY = D(2026, 10, 10)
YEARS = frozenset({2026, 2027})


@pytest.fixture(scope="module")
def cols():
    return load_columns()


@pytest.fixture
def csv_path(tmp_path, cols):
    p = tmp_path / "series.csv"
    p.write_text(",".join(header(cols)) + "\n", encoding="utf-8")
    return p


def ok(payload, cols, known=()):
    return validate(
        payload, cols, known_dates=set(known), covered_years=YEARS, today=TODAY
    )


def rejects(payload, cols, known=(), match=None):
    with pytest.raises(ValidationError, match=match):
        ok(payload, cols, known)


# --------------------------- 단위·척도 사고 ---------------------------

def test_unit_mistake_in_fx_is_rejected(cols):
    """원/달러를 1350이 아니라 13.5로 적는 것이 가장 흔한 사고다."""
    rejects({"date": "2026-10-09", "usdkrw": 13.5, "source": "t"}, cols, match="가드 범위")


def test_rate_written_as_basis_points_is_rejected(cols):
    """금리에 퍼센트와 bp를 섞는 사고."""
    rejects({"date": "2026-10-09", "cgb_3y": 325, "source": "t"}, cols, match="가드 범위")


def test_yen_written_per_single_yen_is_rejected(cols):
    rejects(
        {"date": "2026-10-09", "jpykrw_100": 9.1, "source": "t"}, cols, match="가드 범위"
    )


def test_plausible_values_pass(cols):
    row = ok(
        {
            "date": "2026-10-09",
            "cgb_3y": 2.915,
            "usdkrw": "1,352.40",
            "kospi": 2680.11,
            "source": "서울외환시장 종가",
        },
        cols,
    )
    assert row["usdkrw"] == "1352.40"       # 천단위 쉼표를 받아들인다
    assert row["cgb_3y"] == "2.915"          # decimals 자리수로 고정
    assert row["kospi"] == "2680.11"


# ------------------------------ 0과 빈 칸 ------------------------------

def test_zero_is_rejected_where_implausible(cols):
    """확인 못 한 값을 0으로 메우는 것이 가장 나쁜 실패 양식이다."""
    rejects({"date": "2026-10-09", "cgb_3y": 0, "source": "t"}, cols, match="0은 받지 않는다")


def test_zero_is_allowed_for_swap_point(cols):
    """스왑포인트는 0이 실제로 나올 수 있는 값이다."""
    row = ok({"date": "2026-10-09", "swap_point_1y": 0, "source": "t"}, cols)
    assert row["swap_point_1y"] == "0.00"


def test_negative_swap_point_is_allowed(cols):
    row = ok({"date": "2026-10-09", "swap_point_1y": -11.25, "source": "t"}, cols)
    assert row["swap_point_1y"] == "-11.25"


def test_blank_values_are_kept_blank(cols):
    row = ok({"date": "2026-10-09", "usdkrw": 1350, "cgb_3y": "", "source": "t"}, cols)
    assert row["cgb_3y"] == ""
    assert row["cd_91"] == ""


def test_row_with_no_values_is_rejected(cols):
    rejects({"date": "2026-10-09", "source": "t"}, cols, match="값이 하나도 없다")


# ------------------------------- 날짜 -------------------------------

def test_future_date_is_rejected(cols):
    rejects({"date": "2099-01-01", "usdkrw": 1350, "source": "t"}, cols, match="미래")


def test_today_is_allowed(cols):
    assert ok({"date": TODAY.isoformat(), "usdkrw": 1350, "source": "t"}, cols)


def test_date_outside_holiday_coverage_is_rejected(cols):
    rejects(
        {"date": "2024-05-02", "usdkrw": 1350, "source": "t"}, cols, match="대장 범위 밖"
    )


def test_bad_date_format_is_rejected(cols):
    rejects({"date": "2026/10/08", "usdkrw": 1350, "source": "t"}, cols, match="형식")


def test_duplicate_date_is_rejected(cols):
    """append-only이므로 덮어쓰지 않는다."""
    rejects(
        {"date": "2026-10-07", "usdkrw": 1350, "source": "t"},
        cols,
        known=["2026-10-07"],
        match="이미 있다",
    )


# ------------------------------- 그 외 -------------------------------

def test_missing_source_is_rejected(cols):
    rejects({"date": "2026-10-09", "usdkrw": 1350}, cols, match="source")


def test_unknown_column_is_rejected(cols):
    rejects(
        {"date": "2026-10-09", "usdkrwx": 1350, "source": "t"}, cols, match="알 수 없는 열"
    )


def test_non_numeric_is_rejected(cols):
    rejects(
        {"date": "2026-10-09", "usdkrw": "일천삼백", "source": "t"},
        cols,
        match="숫자가 아니다",
    )


def test_collected_at_is_filled(cols):
    row = ok({"date": "2026-10-09", "usdkrw": 1350, "source": "t"}, cols)
    assert row["collected_at"].endswith("+09:00")


def test_append_then_dates_round_trip(csv_path, cols):
    row = ok({"date": "2026-10-09", "usdkrw": 1350, "source": "t"}, cols)
    append_row(row, cols, csv_path)
    assert existing_dates(csv_path) == {"2026-10-09"}
    assert read_rows(csv_path)[0]["usdkrw"] == "1350.00"


def test_guard_notes_are_separate_from_display_notes(cols):
    """내부 검증 메모가 산출물로 새어 나가면 안 된다."""
    by_name = {c.name: c for c in cols}
    assert by_name["jpykrw_100"].display_note == "100엔당"
    assert "sane_min" in (by_name["jpykrw_100"].guard_note or "")
    assert by_name["swap_point_1y"].display_note is None
