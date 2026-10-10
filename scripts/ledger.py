"""규제·제도 변경 대장.

`data/regulations/ledger.jsonl`은 **append-only**다. 한 줄에 레코드 하나이고, 과거 줄을
고쳐 쓰지 않는다 (CLAUDE.md). 같은 사안의 진행은 새 레코드를 덧붙여 기록한다.

    python3 scripts/ledger.py add < record.json
    python3 scripts/ledger.py show <id>
    python3 scripts/ledger.py new-since 2026-10-01
    python3 scripts/ledger.py pending
    python3 scripts/ledger.py validate

네트워크를 타지 않는다. 수집은 호출자가 하고, 이 도구는 중복·전이 판정과 조회만 한다.

판정 규칙이 이 도구의 핵심이다. 주 1회 실행이 겹쳐도 대장이 더럽혀지지 않아야 하고,
"그 건 지금 어디까지 갔나"에 답할 수 있어야 한다.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = ROOT / "data" / "regulations" / "ledger.jsonl"
KST = datetime.timezone(datetime.timedelta(hours=9))

# 진행 순서. 뒤로 가는 전이는 오보 정정으로만 허용한다.
STATUS_ORDER = ["입법예고", "규정변경예고", "의결", "공포", "시행"]
CATEGORIES = ["자금·유동성", "보험회계", "세무", "자본규제", "기타"]
# primary(감독당국·법령 원문 확인) > search-only(검색 결과만)
CONFIDENCE_ORDER = ["search-only", "primary"]

REQUIRED = ("source", "title", "status", "category", "url", "confidence")
DATE_FIELDS = ("announced_on", "comment_due", "effective_on")
TEXT_FIELDS = ("transitional", "impact", "todo")


class LedgerError(Exception):
    """적재를 거부한 이유. 걸리면 아무것도 쓰지 않는다."""


class Duplicate(LedgerError):
    """이미 같은 상태로 들어와 있다."""


def normalize_url(url: str) -> str:
    """쿼리스트링과 프래그먼트를 버린다.

    같은 공고가 목록 페이지 번호만 다른 링크로 두 번 들어오는 일이 흔하다
    (예: .../84439?curPage=5 와 .../84439?curPage=42 는 같은 글이다).
    """
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip()


def make_id(url: str, title: str) -> str:
    seed = f"{normalize_url(url)}|{normalize_title(title)}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def rank(value: str, order: list[str], field: str) -> int:
    try:
        return order.index(value)
    except ValueError:
        raise LedgerError(f"{field}가 {order} 중 하나가 아니다 — {value!r}") from None


def parse_date(value: object, field: str) -> str | None:
    """날짜를 모르면 null로 둔다. '미확인'을 그럴듯한 날짜로 메우지 않는다."""
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text in {"미확인", "null", "none"}:
        return None
    try:
        return datetime.date.fromisoformat(text).isoformat()
    except ValueError:
        raise LedgerError(f"{field}가 YYYY-MM-DD 형식이 아니다 — {text!r}") from None


def read_ledger(path: Path | str = LEDGER_PATH) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise LedgerError(f"{p}:{n} 줄이 JSON이 아니다 — {e}") from None
    return out


def revisions(records: list[dict], item_id: str) -> list[dict]:
    return sorted(
        (r for r in records if r["id"] == item_id), key=lambda r: r["rev"]
    )


def build(payload: dict, records: list[dict], *, today: datetime.date, force: bool) -> dict:
    """검증·판정을 거친 새 레코드. 중복이면 Duplicate를 낸다."""
    missing = [f for f in REQUIRED if not str(payload.get(f, "")).strip()]
    if missing:
        raise LedgerError(f"필수 필드가 비었다: {missing}")

    status = str(payload["status"]).strip()
    confidence = str(payload["confidence"]).strip()
    category = str(payload["category"]).strip()
    status_rank = rank(status, STATUS_ORDER, "status")
    conf_rank = rank(confidence, CONFIDENCE_ORDER, "confidence")
    if category not in CATEGORIES:
        raise LedgerError(f"category가 {CATEGORIES} 중 하나가 아니다 — {category!r}")

    url = str(payload["url"]).strip()
    title = normalize_title(str(payload["title"]))
    item_id = make_id(url, title)
    history = revisions(records, item_id)

    change: str | None = None
    supersedes: str | None = None
    rev = 1
    first_seen = today.isoformat()

    if history:
        latest = history[-1]
        rev = latest["rev"] + 1
        supersedes = f"{item_id}#{latest['rev']}"
        first_seen = latest["first_seen"]
        prev_status_rank = rank(latest["status"], STATUS_ORDER, "status")
        prev_conf_rank = rank(latest["confidence"], CONFIDENCE_ORDER, "confidence")

        if status_rank > prev_status_rank:
            change = f"{latest['status']} → {status}"
        elif status_rank == prev_status_rank and conf_rank > prev_conf_rank:
            # 원문을 확인한 것도 추적할 가치가 있는 변화다.
            change = f"출처 확인 {latest['confidence']} → {confidence}"
        elif status_rank == prev_status_rank and conf_rank == prev_conf_rank:
            raise Duplicate(
                f"{item_id} 는 이미 '{status}' / {confidence} 로 들어와 있다 "
                f"(rev {latest['rev']}, {latest['last_updated']})"
            )
        else:
            back = (
                f"{latest['status']} → {status}"
                if status_rank < prev_status_rank
                else f"{latest['confidence']} → {confidence}"
            )
            if not force:
                raise LedgerError(
                    f"{item_id} 는 뒤로 가는 변경이다 ({back}). 오보 정정이면 "
                    f"--force 로만 넣는다"
                )
            change = f"정정 {back}"

    record = {
        "id": item_id,
        "rev": rev,
        "source": str(payload["source"]).strip(),
        "title": title,
        "status": status,
        "category": category,
        "url": url,
        "confidence": confidence,
        "announced_on": parse_date(payload.get("announced_on"), "announced_on"),
        "comment_due": parse_date(payload.get("comment_due"), "comment_due"),
        "effective_on": parse_date(payload.get("effective_on"), "effective_on"),
    }
    for f in TEXT_FIELDS:
        value = payload.get(f)
        record[f] = normalize_title(str(value)) if value else None
    record.update(
        {
            "first_seen": first_seen,
            "last_updated": today.isoformat(),
            "supersedes": supersedes,
            "change": change,
            "corrected": bool(force and change and change.startswith("정정")),
        }
    )
    return record


def append(record: dict, path: Path | str = LEDGER_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def latest_by_id(records: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in records:
        cur = out.get(r["id"])
        if cur is None or r["rev"] > cur["rev"]:
            out[r["id"]] = r
    return out


# ------------------------------- 하위 명령 -------------------------------

def cmd_add(args) -> int:
    payload = json.load(args.file) if args.file else json.load(sys.stdin)
    records = read_ledger(args.ledger)
    today = (
        datetime.date.fromisoformat(args.today)
        if args.today
        else datetime.datetime.now(KST).date()
    )
    try:
        record = build(payload, records, today=today, force=args.force)
    except Duplicate as e:
        print(f"중복: {e}", file=sys.stderr)
        return 4
    except LedgerError as e:
        print(f"거부: {e}", file=sys.stderr)
        return 2

    if not args.dry_run:
        append(record, args.ledger)
    kind = "신규" if record["rev"] == 1 else f"전이 ({record['change']})"
    prefix = "검증 통과 (쓰지 않음)" if args.dry_run else "추가"
    print(f"{prefix}: {record['id']}#{record['rev']} {kind}", file=sys.stderr)
    json.dump(record, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


def cmd_show(args) -> int:
    history = revisions(read_ledger(args.ledger), args.id)
    if not history:
        print(f"{args.id} 는 대장에 없다", file=sys.stderr)
        return 1
    json.dump(
        {"id": args.id, "revisions": len(history), "history": history},
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    print()
    return 0


def cmd_new_since(args) -> int:
    since = datetime.date.fromisoformat(args.date)
    out = [
        {
            "kind": "신규" if r["rev"] == 1 else "전이",
            **r,
        }
        for r in read_ledger(args.ledger)
        if datetime.date.fromisoformat(r["last_updated"]) >= since
    ]
    out.sort(key=lambda r: (r["last_updated"], r["category"], r["id"]))
    json.dump(
        {
            "since": since.isoformat(),
            "count": len(out),
            "new": sum(1 for r in out if r["kind"] == "신규"),
            "transitions": sum(1 for r in out if r["kind"] == "전이"),
            "search_only": sum(1 for r in out if r["confidence"] == "search-only"),
            "records": out,
        },
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    print()
    return 0


def cmd_pending(args) -> int:
    today = (
        datetime.date.fromisoformat(args.today)
        if args.today
        else datetime.datetime.now(KST).date()
    )
    horizon = today + datetime.timedelta(days=args.within)
    out = []
    for r in latest_by_id(read_ledger(args.ledger)).values():
        reasons = []
        eff, due = r.get("effective_on"), r.get("comment_due")
        if eff and datetime.date.fromisoformat(eff) >= today:
            reasons.append("시행 예정")
        if due and today <= datetime.date.fromisoformat(due) <= horizon:
            reasons.append("의견제출 기한 임박")
        if r["status"] != "시행" and not eff:
            reasons.append("시행일 미확인")
        if reasons:
            out.append({"reasons": reasons, **r})
    out.sort(key=lambda r: (r.get("effective_on") or "9999-12-31", r["id"]))
    json.dump(
        {"today": today.isoformat(), "within_days": args.within,
         "count": len(out), "records": out},
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    print()
    return 0


def cmd_validate(args) -> int:
    records = read_ledger(args.ledger)
    problems: list[str] = []
    by_id: dict[str, list[dict]] = {}
    for r in records:
        for f in ("id", "rev", *REQUIRED, "first_seen", "last_updated"):
            if f not in r:
                problems.append(f"{r.get('id', '?')}: 필드 누락 {f}")
        by_id.setdefault(r.get("id", "?"), []).append(r)

    for item_id, group in by_id.items():
        group = sorted(group, key=lambda r: r["rev"])
        if [r["rev"] for r in group] != list(range(1, len(group) + 1)):
            problems.append(f"{item_id}: rev가 1부터 연속이 아니다 — "
                            f"{[r['rev'] for r in group]}")
        if group[0].get("supersedes") is not None:
            problems.append(f"{item_id}: rev 1의 supersedes가 비어 있지 않다")
        for prev, cur in zip(group, group[1:]):
            if cur.get("supersedes") != f"{item_id}#{prev['rev']}":
                problems.append(
                    f"{item_id}#{cur['rev']}: supersedes가 직전 rev를 가리키지 않는다"
                )
            if cur.get("corrected"):
                continue
            if rank(cur["status"], STATUS_ORDER, "status") < rank(
                prev["status"], STATUS_ORDER, "status"
            ):
                problems.append(
                    f"{item_id}#{cur['rev']}: 정정 표시 없이 상태가 뒤로 갔다"
                )
        expected = make_id(group[0]["url"], group[0]["title"])
        if item_id != expected:
            problems.append(f"{item_id}: id가 url+title 해시와 다르다 (기대 {expected})")

    json.dump(
        {"records": len(records), "items": len(by_id),
         "problems": problems, "ok": not problems},
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    print()
    return 0 if not problems else 5


def main() -> int:
    ap = argparse.ArgumentParser(description="규제·제도 변경 대장")
    ap.add_argument("--ledger", default=str(LEDGER_PATH))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="레코드 추가 (중복·전이 판정)")
    p.add_argument("file", nargs="?", type=argparse.FileType(encoding="utf-8"))
    p.add_argument("--force", action="store_true", help="뒤로 가는 변경을 정정으로 허용")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--today")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("show", help="한 건의 전체 이력")
    p.add_argument("id")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("new-since", help="그 날짜 이후 신규·전이")
    p.add_argument("date")
    p.set_defaults(func=cmd_new_since)

    p = sub.add_parser("pending", help="시행 예정·기한 임박·시행일 미확인")
    p.add_argument("--within", type=int, default=30, help="의견제출 기한 임박 판정 일수")
    p.add_argument("--today")
    p.set_defaults(func=cmd_pending)

    p = sub.add_parser("validate", help="대장 무결성 검사")
    p.set_defaults(func=cmd_validate)

    args = ap.parse_args()
    try:
        return args.func(args)
    except LedgerError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
