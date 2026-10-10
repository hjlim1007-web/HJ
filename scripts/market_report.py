"""시장지표 월간 리뷰 HTML을 만든다.

    python3 scripts/market_report.py --month 2026-09 -o review.html
    python3 scripts/market_report.py --month 2026-09 --csv tests/fixtures/series-sample.csv \
      --note "국고채 3년이 월중 20bp 상승 — 재투자 수익률에는 유리, 보유 채권 평가손익에는 불리"

조판을 스크립트에 고정한다 — 매달 LLM이 다시 조판하면 결과가 흔들린다.
해석 문장은 **자동 생성하지 않는다.** 계산된 사실(고·저·평균·전월 대비)만 싣고,
판단은 `--note`로 받은 것만 넣는다. 근거 없는 시장 해설을 스크립트가 쓰게 하지 않는다.

차트 설계 (dataviz 스킬 기준)
- 금리·환율·지수는 척도가 서로 달라 **이중축을 쓰지 않고 스몰 멀티플**로 나눈다.
- 시리즈가 하나씩이므로 **범례를 두지 않는다** — 제목이 시리즈를 가리킨다.
- 기준선이 0이 아니므로 막대가 아니라 **선**이다(막대는 단일 기준선에서 자라야 한다).
- 값이 빈 날은 선을 끊는다. **보간하지 않는다** — 없는 데이터를 이어 그리면 추세를 왜곡한다.
- 선 색은 `#0e7c86`. 브랜드 청록 `#01c1d6`은 흰 배경 대비가 2.13:1로 3:1에 못 미쳐
  (검증기 WARN) 2px 선으로 쓰기에 너무 옅다. 청록은 라벨에만 남긴다.
- 메일에는 호버가 없으므로, 수치 표가 그 자리를 대신한다(접근성 패스의 table view).

알려진 한계: 인라인 SVG는 아이폰·애플 메일(WebKit)에서는 렌더되지만 Outlook 등 일부
클라이언트는 지우거나 그리지 못한다. 그래서 고·저·평균·전월 대비는 **표로도 전부** 싣는다 —
그림이 사라져도 내용이 남는다.
"""

from __future__ import annotations

import argparse
import datetime
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from mailstyle import (
    C_ACCENT,
    C_BAND,
    C_BODY,
    C_HAIR,
    C_MUTED,
    C_RULE,
    C_TITLE,
    SIZE_BODY,
    SIZE_SECTION,
    SIZE_SMALL,
    delta_mark,
    esc,
    fmt_date,
    page,
)
from market_series import SERIES_PATH, Column, load_columns, read_rows

LINE = "#0e7c86"          # 검증 통과한 선 색
SPARK_W, SPARK_H, PAD = 300, 40, 4


@dataclass
class Stat:
    col: Column
    points: list[float | None]      # 월중 각 관측행의 값 (없으면 None)
    last: float
    last_date: str
    high: float
    low: float
    mean: float
    count: int
    delta: float | None             # 전월 최종 관측 대비
    prev_last_date: str | None


def month_bounds(month: str) -> tuple[datetime.date, datetime.date]:
    y, m = (int(x) for x in month.split("-"))
    start = datetime.date(y, m, 1)
    end = datetime.date(y + (m == 12), (m % 12) + 1, 1) - datetime.timedelta(days=1)
    return start, end


def to_float(text: str) -> float | None:
    text = (text or "").strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def collect(rows: list[dict], cols: list[Column], month: str) -> tuple[list[Stat], dict]:
    start, end = month_bounds(month)
    dated = sorted(
        (r for r in rows if r.get("date")),
        key=lambda r: r["date"],
    )
    in_month = [r for r in dated if start.isoformat() <= r["date"] <= end.isoformat()]
    before = [r for r in dated if r["date"] < start.isoformat()]

    stats: list[Stat] = []
    for col in cols:
        points = [to_float(r.get(col.name, "")) for r in in_month]
        seen = [(r["date"], v) for r, v in zip(in_month, points) if v is not None]
        if len(seen) < 2:
            # 관측이 1개 이하면 월중 추이를 말할 수 없다. 싣지 않는다.
            continue
        values = [v for _, v in seen]

        prev = None
        for r in reversed(before):
            v = to_float(r.get(col.name, ""))
            if v is not None:
                prev = (r["date"], v)
                break

        stats.append(
            Stat(
                col=col,
                points=points,
                last=seen[-1][1],
                last_date=seen[-1][0],
                high=max(values),
                low=min(values),
                mean=statistics.fmean(values),
                count=len(values),
                delta=(seen[-1][1] - prev[1]) if prev else None,
                prev_last_date=prev[0] if prev else None,
            )
        )

    meta = {
        "rows_in_month": len(in_month),
        "first": in_month[0]["date"] if in_month else None,
        "last": in_month[-1]["date"] if in_month else None,
        "sources": sorted({r.get("source", "") for r in in_month if r.get("source")}),
    }
    return stats, meta


def sparkline(points: list[float | None]) -> str:
    """결측 구간을 끊은 2px 선. 범례도 축도 없다 — 수치는 아래 표가 말한다."""
    values = [v for v in points if v is not None]
    lo, hi = min(values), max(values)
    span = hi - lo
    n = len(points)

    def x(i: int) -> float:
        return PAD + (SPARK_W - 2 * PAD) * (i / (n - 1) if n > 1 else 0.5)

    def y(v: float) -> float:
        if span == 0:
            return SPARK_H / 2
        return PAD + (SPARK_H - 2 * PAD) * (1 - (v - lo) / span)

    segments: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for i, v in enumerate(points):
        if v is None:
            if current:
                segments.append(current)
                current = []
            continue
        current.append((x(i), y(v)))
    if current:
        segments.append(current)

    parts = []
    for seg in segments:
        if len(seg) == 1:
            cx, cy = seg[0]
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2" fill="{LINE}"/>')
        else:
            pts = " ".join(f"{px:.1f},{py:.1f}" for px, py in seg)
            parts.append(
                f'<polyline points="{pts}" fill="none" stroke="{LINE}" '
                f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
            )
    # 마지막 관측에 끝점 마커를 둔다. 값 라벨은 모든 점에 달지 않는다.
    last_i = max(i for i, v in enumerate(points) if v is not None)
    parts.append(
        f'<circle cx="{x(last_i):.1f}" cy="{y(points[last_i]):.1f}" r="4" '
        f'fill="{LINE}" stroke="#ffffff" stroke-width="2"/>'
    )
    return (
        f'<svg viewBox="0 0 {SPARK_W} {SPARK_H}" width="{SPARK_W}" height="{SPARK_H}" '
        f'style="width:100%;max-width:{SPARK_W}px;height:{SPARK_H}px;display:block;" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="월중 추이">{"".join(parts)}</svg>'
    )


def render_stat(s: Stat) -> str:
    d = s.col.decimals
    gap = s.col.unit if s.col.unit != "%" else "%p"
    # guard_note는 내부 메모이므로 싣지 않는다 — 독자용 display_note만 쓴다.
    sub = s.col.unit + (f" · {s.col.display_note}" if s.col.display_note else "")

    row_a = (
        f'<tr><td style="padding:16px 0 0;font-size:{SIZE_BODY}px;color:{C_BODY};">'
        f'{esc(s.col.label)}'
        f'<div style="font-size:{SIZE_SMALL}px;color:{C_MUTED};padding-top:2px;">'
        f"{esc(sub)}</div></td>"
        f'<td align="right" style="padding:16px 0 0;font-size:{SIZE_BODY}px;'
        f'color:{C_TITLE};white-space:nowrap;">{s.last:,.{d}f}'
        f'<div style="font-size:{SIZE_SMALL}px;padding-top:2px;">'
        f"{delta_mark(s.delta, d)} {esc(gap)}</div></td></tr>"
    )
    facts = (
        f"고 {s.high:,.{d}f} · 저 {s.low:,.{d}f} · 평균 {s.mean:,.{d}f} · "
        f"관측 {s.count}일 · 월말 {s.last_date}"
    )
    if s.prev_last_date:
        facts += f" · 전월 기준 {s.prev_last_date}"
    row_b = (
        f'<tr><td colspan="2" style="padding:8px 0 16px;'
        f'border-bottom:1px solid {C_HAIR};">{sparkline(s.points)}'
        f'<div style="font-size:{SIZE_SMALL}px;color:{C_MUTED};padding-top:6px;'
        f'line-height:1.6;">{esc(facts)}</div></td></tr>'
    )
    return row_a + row_b


def render(stats: list[Stat], meta: dict, month: str, notes: list[str]) -> str:
    body = [
        f'<tr><td colspan="2" style="padding:0 0 4px;">'
        f'<div style="font-size:{SIZE_SECTION}px;font-weight:600;color:{C_TITLE};">'
        f"월중 추이</div></td></tr>"
    ]
    body.extend(render_stat(s) for s in stats)

    if notes:
        inner = "".join(
            f'<div style="font-size:{SIZE_BODY}px;color:{C_BODY};line-height:1.7;'
            f'padding-top:6px;">{esc(n)}</div>'
            for n in notes
        )
    else:
        inner = (
            f'<div style="font-size:{SIZE_BODY}px;color:{C_MUTED};line-height:1.7;'
            f"padding-top:6px;\">자동으로 채우지 않는다 — 금리·환율 방향에 대한 판단은 "
            f"작성자가 적는다 (--note).</div>"
        )
    body.append(
        f'<tr><td colspan="2" style="padding:24px 0 0;border-top:1px solid {C_RULE};">'
        f'<div style="background:{C_BAND};padding:14px 16px;margin-top:18px;">'
        f'<div style="font-size:{SIZE_SMALL}px;color:{C_ACCENT};">해석</div>'
        f"{inner}</div></td></tr>"
    )

    footnotes = [
        f"대상 {month} · 관측 {meta['rows_in_month']}일"
        + (f" ({meta['first']} ~ {meta['last']})" if meta["first"] else ""),
        "값이 빈 날은 선을 끊었다. 보간하지 않는다.",
        "전월 대비는 전월 최종 관측값 기준이다.",
    ]
    if meta["sources"]:
        footnotes.append("출처: " + ", ".join(meta["sources"]))

    header = [f"{month}", f"지표 {len(stats)}종"]
    return page(
        title="월간 자금시장 리뷰",
        header_lines=header,
        body="".join(body),
        footnotes=footnotes,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="시장지표 월간 리뷰")
    ap.add_argument("--month", required=True, help="대상 월 YYYY-MM")
    ap.add_argument("--csv", default=str(SERIES_PATH))
    ap.add_argument("--note", action="append", default=[], help="해석 문장 (여러 번 가능)")
    ap.add_argument("-o", "--out", help="출력 파일 (기본: 표준 출력)")
    args = ap.parse_args()

    try:
        month_bounds(args.month)
    except (ValueError, IndexError):
        print(f"--month은 YYYY-MM 형식이어야 한다 — {args.month!r}", file=sys.stderr)
        return 2

    cols = load_columns()
    rows = read_rows(args.csv)
    stats, meta = collect(rows, cols, args.month)

    if not stats:
        print(
            f"{args.month}에 관측이 2일 이상인 지표가 없다 — 리뷰를 만들지 않는다",
            file=sys.stderr,
        )
        return 3

    print(f"SUBJECT: [월간 리뷰] {args.month} 자금시장 지표 {len(stats)}종", file=sys.stderr)
    out = render(stats, meta, args.month, args.note)
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"작성: {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
