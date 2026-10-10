"""시장지표 시계열의 스키마와 읽기·쓰기.

`data/market/columns.yaml`이 열 정의의 정본이고, `data/market/series.csv`가 데이터다.
CSV는 **append-only**로 다룬다 — 과거 행을 고쳐 쓰지 않는다 (CLAUDE.md).

네트워크를 타지 않는다. 수집은 호출자가 하고, 이 모듈은 검증과 적재만 한다.
"""

from __future__ import annotations

import csv
import datetime
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
COLUMNS_PATH = ROOT / "data" / "market" / "columns.yaml"
SERIES_PATH = ROOT / "data" / "market" / "series.csv"

META_FIELDS = ("date", "source", "collected_at")


class ValidationError(Exception):
    """적재를 거부한 이유. 하나라도 걸리면 아무것도 쓰지 않는다."""


@dataclass(frozen=True)
class Column:
    name: str
    label: str
    unit: str
    decimals: int
    sane_min: float
    sane_max: float
    reject_zero: bool
    display_note: str | None = None   # 산출물에 보이는 설명
    guard_note: str | None = None     # 내부 메모. 산출물에 내보내지 않는다


def load_columns(path: Path | str = COLUMNS_PATH) -> list[Column]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    cols = [
        Column(
            name=c["name"],
            label=c["label"],
            unit=c["unit"],
            decimals=int(c["decimals"]),
            sane_min=float(c["sane_min"]),
            sane_max=float(c["sane_max"]),
            reject_zero=bool(c["reject_zero"]),
            display_note=c.get("display_note"),
            guard_note=c.get("guard_note"),
        )
        for c in raw["columns"]
    ]
    names = [c.name for c in cols]
    if len(names) != len(set(names)):
        raise ValueError("columns.yaml에 중복된 열 이름이 있다")
    return cols


def header(cols: list[Column]) -> list[str]:
    return ["date", *[c.name for c in cols], "source", "collected_at"]


def read_rows(path: Path | str = SERIES_PATH) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def existing_dates(path: Path | str = SERIES_PATH) -> set[str]:
    return {r["date"] for r in read_rows(path) if r.get("date")}


def parse_value(col: Column, raw: object) -> float | None:
    """빈 값은 None으로. 숫자가 아니거나 범위 밖이면 ValidationError."""
    if raw is None:
        return None
    text = str(raw).strip().replace(",", "")
    if text == "":
        return None
    try:
        value = float(text)
    except ValueError:
        raise ValidationError(
            f"{col.name}({col.label}): 숫자가 아니다 — {raw!r}"
        ) from None
    if value == 0 and col.reject_zero:
        raise ValidationError(
            f"{col.name}({col.label}): 0은 받지 않는다. 확인하지 못한 값은 "
            f"0으로 메우지 말고 빈 칸으로 둔다"
        )
    if not (col.sane_min <= value <= col.sane_max):
        raise ValidationError(
            f"{col.name}({col.label}): {value:g}{col.unit}는 가드 범위 "
            f"{col.sane_min:g}~{col.sane_max:g} 밖이다. 단위를 확인하라 "
            f"(흔한 실수: 원/달러를 13.5, 금리를 bp로 적는 것)"
        )
    return value


def validate(
    payload: dict,
    cols: list[Column],
    *,
    known_dates: set[str],
    covered_years: frozenset[int] | set[int],
    today: datetime.date,
) -> dict[str, str]:
    """검증을 통과한 한 행을 CSV에 쓸 문자열 dict으로 돌려준다."""
    unknown = set(payload) - {c.name for c in cols} - set(META_FIELDS)
    if unknown:
        raise ValidationError(
            f"알 수 없는 열: {sorted(unknown)} — columns.yaml에 없는 이름이다"
        )

    raw_date = str(payload.get("date", "")).strip()
    if not raw_date:
        raise ValidationError("date가 비어 있다")
    try:
        d = datetime.date.fromisoformat(raw_date)
    except ValueError:
        raise ValidationError(f"date가 YYYY-MM-DD 형식이 아니다 — {raw_date!r}") from None
    if d > today:
        raise ValidationError(f"date가 미래다 — {d.isoformat()} (오늘 {today.isoformat()})")
    if d.year not in covered_years:
        raise ValidationError(
            f"date {d.isoformat()}는 공휴일 대장 범위 밖이다 "
            f"(수록 연도: {sorted(covered_years)}). data/holidays.yaml을 갱신하라"
        )
    if d.isoformat() in known_dates:
        raise ValidationError(
            f"{d.isoformat()} 행이 이미 있다. series.csv는 append-only이므로 "
            f"덮어쓰지 않는다"
        )

    source = str(payload.get("source", "")).strip()
    if not source:
        raise ValidationError("source가 비어 있다 — 어디서 가져온 값인지 반드시 남긴다")

    row: dict[str, str] = {"date": d.isoformat(), "source": source}
    filled = 0
    for col in cols:
        value = parse_value(col, payload.get(col.name))
        if value is None:
            row[col.name] = ""
        else:
            row[col.name] = f"{value:.{col.decimals}f}"
            filled += 1

    if filled == 0:
        raise ValidationError("값이 하나도 없다 — 빈 행을 쌓지 않는다")

    row["collected_at"] = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=9))
    ).isoformat(timespec="seconds")
    return row


def append_row(row: dict[str, str], cols: list[Column], path: Path | str = SERIES_PATH):
    p = Path(path)
    new_file = not p.exists() or p.stat().st_size == 0
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header(cols))
        if new_file:
            w.writeheader()
        w.writerow(row)
