import re
from pathlib import Path

import pytest

from market_report import collect, month_bounds, render, sparkline
from market_series import load_columns, read_rows

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "series-sample.csv"


@pytest.fixture(scope="module")
def built():
    cols = load_columns()
    rows = read_rows(FIXTURE)
    stats, meta = collect(rows, cols, "2026-09")
    return stats, meta, render(stats, meta, "2026-09", [])


def test_month_bounds():
    assert month_bounds("2026-09") == (__import__("datetime").date(2026, 9, 1),
                                       __import__("datetime").date(2026, 9, 30))
    assert month_bounds("2026-12")[1].isoformat() == "2026-12-31"
    assert month_bounds("2028-02")[1].isoformat() == "2028-02-29"   # 윤년


def test_series_with_one_observation_is_excluded(built):
    """관측이 1개 이하면 월중 추이를 말할 수 없다."""
    stats, _, html = built
    assert "dxy" not in {s.col.name for s in stats}
    assert "달러인덱스" not in html


def test_stats_are_computed_from_data(built):
    stats, _, _ = built
    s = next(s for s in stats if s.col.name == "cgb_3y")
    assert s.low <= s.mean <= s.high
    assert s.count == 22
    assert s.delta is not None          # 전월 관측이 있으므로 비교된다


def test_missing_days_reduce_the_count(built):
    """픽스처의 CD 91일은 9/10~9/14 결측이다.

    그 구간의 주말(9/12 토, 9/13 일)은 애초에 행이 없으므로 결측 영업일은
    9/10·9/11·9/14 세 날이다 — 22일 중 19일만 관측으로 남는다.
    """
    stats, _, _ = built
    cd = next(s for s in stats if s.col.name == "cd_91")
    cgb = next(s for s in stats if s.col.name == "cgb_3y")
    assert cgb.count == 22                      # 결측 없는 지표
    assert cd.count == cgb.count - 3
    assert sum(1 for v in cd.points if v is None) == 3


# --------------------------- 스파크라인 ---------------------------

def test_gap_breaks_the_line_and_is_not_interpolated():
    """없는 데이터를 이어 그리면 추세를 왜곡한다."""
    svg = sparkline([1.0, 2.0, None, None, 3.0, 4.0])
    assert svg.count("<polyline") == 2


def test_continuous_series_is_one_segment():
    assert sparkline([1.0, 2.0, 3.0]).count("<polyline") == 1


def test_lone_point_between_gaps_is_a_dot():
    svg = sparkline([1.0, 2.0, None, 5.0, None, 3.0, 4.0])
    assert "<circle" in svg


def test_flat_series_does_not_divide_by_zero():
    svg = sparkline([2.5, 2.5, 2.5])
    assert "<polyline" in svg
    assert "nan" not in svg.lower()


def test_endpoint_marker_sits_on_the_last_observation():
    """값 라벨을 모든 점에 달지 않고, 끝점만 표시한다."""
    svg = sparkline([1.0, 2.0, 3.0, None])
    assert svg.count('r="4"') == 1


def test_sparkline_has_no_legend_or_axis():
    """시리즈가 하나이므로 범례를 두지 않는다 — 제목이 시리즈를 가리킨다."""
    svg = sparkline([1.0, 2.0, 3.0])
    for banned in ("<text", "legend", "<line"):
        assert banned not in svg


# ------------------------------ 조판 ------------------------------

def test_report_is_mobile_safe(built):
    _, _, html = built
    assert 'width="100%"' in html
    assert "max-width:680px" in html
    assert not re.search(r'<table[^>]*width="\d+"', html)
    assert "word-break:keep-all" in html


def test_report_has_no_external_resources(built):
    _, _, html = built
    for banned in ("<script", "<link", "@media", "@import", "googleapis"):
        assert banned not in html


def test_report_font_sizes_follow_the_spec(built):
    _, _, html = built
    sizes = {int(m) for m in re.findall(r"font-size:(\d+)px", html)}
    assert sizes <= {0, 13, 14, 16, 19, 28}, f"사양 밖 글자 크기: {sizes}"


def test_numbers_table_survives_without_svg(built):
    """SVG를 지우는 메일 클라이언트에서도 내용이 남아야 한다."""
    _, _, html = built
    stripped = re.sub(r"<svg.*?</svg>", "", html, flags=re.S)
    assert "고 " in stripped and "평균 " in stripped and "관측 " in stripped


def test_guard_notes_do_not_leak_into_output(built):
    """columns.yaml의 내부 메모는 산출물에 나가지 않는다."""
    _, _, html = built
    assert "sane_min" not in html
    assert "거부하지 않는다" not in html
    assert "100엔당" in html          # 독자용 설명은 남는다


def test_interpretation_is_not_auto_written(built):
    """근거 없는 시장 해설을 스크립트가 쓰게 하지 않는다."""
    _, _, html = built
    assert "자동으로 채우지 않는다" in html


def test_notes_are_rendered_when_given(built):
    stats, meta, _ = built
    html = render(stats, meta, "2026-09", ["금리 상승은 재투자에 유리하다"])
    assert "금리 상승은 재투자에 유리하다" in html
    assert "자동으로 채우지 않는다" not in html


def test_empty_month_yields_no_stats():
    cols = load_columns()
    stats, meta = collect(read_rows(FIXTURE), cols, "2026-11")
    assert stats == []
    assert meta["rows_in_month"] == 0


def test_fixture_source_marks_itself_synthetic(built):
    """픽스처로 만든 리뷰는 합성 데이터임이 드러나야 한다."""
    _, meta, html = built
    assert any("합성" in s for s in meta["sources"])
    assert "합성" in html
