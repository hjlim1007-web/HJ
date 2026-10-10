import datetime
import json
from pathlib import Path

import pytest

from ledger import (
    Duplicate,
    LedgerError,
    append,
    build,
    make_id,
    normalize_url,
    read_ledger,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TODAY = datetime.date(2026, 10, 10)


def fx(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def ledger(tmp_path):
    """add를 순서대로 적용하고 그때그때 레코드를 돌려주는 도우미."""
    path = tmp_path / "ledger.jsonl"

    def add(payload, *, force=False, today=TODAY):
        records = read_ledger(path)
        record = build(payload, records, today=today, force=force)
        append(record, path)
        return record

    add.path = path
    return add


# ------------------------------ id 정규화 ------------------------------

def test_query_string_is_dropped_from_id():
    """같은 공고가 목록 페이지 번호만 다른 링크로 두 번 들어오는 일이 흔하다."""
    a = "https://www.fsc.go.kr/no010101/84439?curPage=5"
    b = "https://www.fsc.go.kr/no010101/84439?curPage=42#content"
    assert normalize_url(a) == normalize_url(b)
    assert make_id(a, "같은 제목") == make_id(b, "같은 제목")


def test_trailing_slash_and_case_do_not_change_id():
    assert make_id("https://WWW.FSC.GO.KR/x/1/", "T") == make_id(
        "https://www.fsc.go.kr/x/1", "T"
    )


def test_different_title_is_a_different_item():
    url = "https://www.fsc.go.kr/x/1"
    assert make_id(url, "가") != make_id(url, "나")


def test_whitespace_in_title_is_collapsed():
    url = "https://www.fsc.go.kr/x/1"
    assert make_id(url, "보험업  감독규정\n개정") == make_id(url, "보험업 감독규정 개정")


# ------------------------- 중복·전이 판정 -------------------------

def test_new_item_starts_at_rev_1(ledger):
    r = ledger(fx("reg-announce.json"))
    assert r["rev"] == 1
    assert r["supersedes"] is None
    assert r["change"] is None
    assert r["first_seen"] == TODAY.isoformat()


def test_same_status_same_confidence_is_duplicate(ledger):
    ledger(fx("reg-announce.json"))
    with pytest.raises(Duplicate):
        ledger(fx("reg-announce.json"))


def test_paginated_duplicate_is_caught(ledger):
    """주 1회 실행이 겹쳐도 대장이 더럽혀지지 않아야 한다."""
    ledger(fx("reg-announce.json"))
    with pytest.raises(Duplicate):
        ledger(fx("reg-announce-paginated.json"))


def test_confidence_upgrade_is_a_transition(ledger):
    """원문을 확인한 것도 추적할 가치가 있는 변화다."""
    ledger(fx("reg-announce.json"))
    r = ledger(fx("reg-announce-primary.json"))
    assert r["rev"] == 2
    assert r["change"] == "출처 확인 search-only → primary"
    assert r["confidence"] == "primary"


def test_status_advance_is_a_transition(ledger):
    ledger(fx("reg-announce.json"))
    ledger(fx("reg-announce-primary.json"))
    r = ledger(fx("reg-resolved.json"))
    assert r["rev"] == 3
    assert r["change"] == "입법예고 → 의결"
    assert r["supersedes"].endswith("#2")


def test_first_seen_is_carried_forward(ledger):
    ledger(fx("reg-announce.json"))
    later = datetime.date(2026, 11, 2)
    r = ledger(fx("reg-resolved.json"), today=later)
    assert r["first_seen"] == TODAY.isoformat()      # 최초 수집일은 유지
    assert r["last_updated"] == later.isoformat()


def test_backward_status_is_rejected(ledger):
    ledger(fx("reg-announce.json"))
    ledger(fx("reg-resolved.json"))
    with pytest.raises(LedgerError, match="뒤로 가는 변경"):
        ledger(fx("reg-announce-primary.json"))


def test_backward_status_allowed_with_force_and_marked(ledger):
    ledger(fx("reg-announce.json"))
    ledger(fx("reg-resolved.json"))
    r = ledger(fx("reg-announce-primary.json"), force=True)
    assert r["corrected"] is True
    assert r["change"].startswith("정정")


# ------------------------------ 검증 ------------------------------

@pytest.mark.parametrize("field", ["source", "title", "status", "category", "url", "confidence"])
def test_required_fields(ledger, field):
    payload = fx("reg-announce.json")
    payload[field] = ""
    with pytest.raises(LedgerError, match="필수 필드"):
        ledger(payload)


def test_unknown_status_is_rejected(ledger):
    payload = fx("reg-announce.json") | {"status": "검토중"}
    with pytest.raises(LedgerError, match="status"):
        ledger(payload)


def test_unknown_category_is_rejected(ledger):
    payload = fx("reg-announce.json") | {"category": "기타등등"}
    with pytest.raises(LedgerError, match="category"):
        ledger(payload)


def test_unknown_confidence_is_rejected(ledger):
    payload = fx("reg-announce.json") | {"confidence": "아마도"}
    with pytest.raises(LedgerError, match="confidence"):
        ledger(payload)


def test_unconfirmed_date_becomes_null_not_a_guess(ledger):
    """'미확인'을 그럴듯한 날짜로 메우지 않는다."""
    payload = fx("reg-announce.json") | {"effective_on": "미확인"}
    assert ledger(payload)["effective_on"] is None


def test_bad_date_is_rejected(ledger):
    payload = fx("reg-announce.json") | {"effective_on": "2027년 1월"}
    with pytest.raises(LedgerError, match="형식"):
        ledger(payload)


def test_fixture_is_not_mistaken_for_real_data():
    """픽스처에는 합성임이 드러나야 한다 — data/에 섞여 들어가면 안 된다."""
    assert "픽스처" in fx("reg-announce.json")["title"]
    assert (FIXTURES / "README.md").exists()
