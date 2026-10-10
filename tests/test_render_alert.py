import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from due import build_alerts
from holidays import load_calendar
from render_alert import render, subject

ROOT = Path(__file__).resolve().parent.parent
D = datetime.date


def payload_for(ref: D) -> dict:
    cal = load_calendar()
    items = yaml.safe_load(
        (ROOT / "data" / "deadlines.yaml").read_text(encoding="utf-8")
    )["deadlines"]
    alerts = build_alerts(items, cal, ref)
    return {
        "reference_date": ref.isoformat(),
        "calendar": {
            "years": sorted(cal.years),
            "updated_on": cal.updated_on.isoformat(),
            "verified_against_primary_source": cal.verified_against_primary_source,
        },
        "alert_count": len(alerts),
        "unverified_count": sum(1 for a in alerts if not a.verified),
        "alerts": [a.to_dict() for a in alerts],
    }


# ------------------------------ 제목 ------------------------------

def test_subject_uses_soonest_lead():
    p = payload_for(D(2026, 11, 10))
    assert subject(p) == "[마감] 2026-11-10(화) D-0 항목 1건"


def test_subject_has_no_duplicate_d0_marker():
    """가장 급한 D-n이 이미 D-0이면 'D-0 포함'을 덧붙이지 않는다."""
    s = subject(payload_for(D(2026, 10, 20)))
    assert s == "[마감] 2026-10-20(화) D-0 항목 2건"
    assert s.count("D-0") == 1


def test_subject_for_future_lead():
    s = subject(payload_for(D(2026, 11, 3)))
    assert s.startswith("[마감] 2026-11-03(화) D-7 항목 1건")


# ------------------------------ 조판 ------------------------------

def test_html_is_mobile_safe():
    """고정폭 table을 쓰면 아이폰 메일이 지면을 축소해 글자가 읽을 수 없게 작아진다."""
    out = render(payload_for(D(2026, 11, 10)))
    assert 'width="100%"' in out
    assert "max-width:680px" in out
    assert not re.search(r'<table[^>]*width="\d+"', out), "고정폭 table이 있다"
    assert "word-break:keep-all" in out


def test_html_has_no_external_resources():
    out = render(payload_for(D(2026, 11, 10)))
    for banned in ("<script", "<link", "@media", "@import", "googleapis"):
        assert banned not in out, f"{banned}가 들어 있다"


def test_body_text_is_at_least_16px():
    """본문을 16px 아래로 내리지 않는다. 13~14px은 라벨·각주 전용."""
    out = render(payload_for(D(2026, 11, 10)))
    sizes = {int(m) for m in re.findall(r"font-size:(\d+)px", out)}
    assert sizes <= {13, 14, 16, 19, 28}, f"사양 밖 글자 크기: {sizes}"


def test_unverified_item_is_flagged():
    out = render(payload_for(D(2026, 11, 10)))
    assert "미검증" in out
    assert "1차 출처로 확인되지 않은 기한" in out


def test_shifted_date_is_disclosed():
    """휴일 보정됐다는 사실 자체가 정보다 — 원래 날짜를 밝힌다."""
    p = payload_for(D(2026, 10, 12))
    assert any(a["shifted"] for a in p["alerts"])
    out = render(p)
    assert "휴일 보정" in out
    assert "2026-10-10(토)" in out


def test_category_headings_only_when_multiple():
    single = render(payload_for(D(2026, 10, 20)))  # 감독보고 2건
    assert single.count("감독보고") == 0, "분류가 1종이면 소제목을 넣지 않는다"


def test_calendar_coverage_warning():
    p = payload_for(D(2026, 11, 10))
    p["calendar"]["years"] = [2025, 2026]  # 다음 해가 없는 상태
    assert "data/holidays.yaml 갱신 필요" in render(p)
    p["calendar"]["years"] = [2026, 2027]
    assert "data/holidays.yaml 갱신 필요" not in render(p)


def test_html_escapes_content():
    p = payload_for(D(2026, 11, 10))
    p["alerts"][0]["name"] = '<img src=x onerror="alert(1)">'
    out = render(p)
    assert "<img" not in out
    assert "&lt;img" in out


# --------------------------- CLI 동작 ---------------------------

def run_cli(*args, stdin=None):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "render_alert.py"), *args],
        capture_output=True,
        text=True,
        input=stdin,
        cwd=ROOT,
    )


def test_cli_quiet_day_exits_3_with_no_html():
    """항목이 없는 날은 종료 코드 3 — 메일을 보내지 않는다는 신호."""
    r = run_cli("--date", "2026-10-14")
    assert r.returncode == 3
    assert r.stdout.strip() == ""
    assert "메일을 보내지 않는다" in r.stderr


def test_cli_emits_subject_on_stderr_and_html_on_stdout():
    r = run_cli("--date", "2026-11-10")
    assert r.returncode == 0
    assert r.stderr.startswith("SUBJECT: [마감] 2026-11-10(화) D-0 항목 1건")
    assert r.stdout.lstrip().startswith("<!doctype html>")


def test_cli_accepts_due_json_on_stdin():
    due = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "due.py"), "--date", "2026-11-10"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    r = run_cli(stdin=due.stdout)
    assert r.returncode == 0
    assert "마감 알림" in r.stdout
