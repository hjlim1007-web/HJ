# HJ

중소 생명보험사 재무회계팀/자금팀 업무 자동화. 규칙과 보안 경계는 `CLAUDE.md`를 먼저 읽는다.

## 무엇이 있는가

| 디렉터리 | 내용 |
|---|---|
| `routines/` | Routine 프롬프트의 정본. 루틴 ↔ trigger id 대조표는 `routines/README.md` |
| `data/deadlines.yaml` | 마감 기한 규칙 (세무·감독보고·결산). 근거 조문과 `verified` 플래그 포함 |
| `data/holidays.yaml` | 공휴일·대체공휴일·근로자의 날 (2026·2027) |
| `data/market/` | 시장지표 시계열. `columns.yaml`이 열 정의의 정본, `series.csv`가 데이터 |
| `data/regulations/` | 규제 변경 대장 `ledger.jsonl` |
| `scripts/` | 순수 계산 스크립트. 네트워크를 타지 않는다 |
| `tests/` | `python3 -m pytest tests/ -v`. 합성 표본은 `tests/fixtures/`에만 둔다 |

## 쓰는 법

```bash
# 오늘(KST) 기준으로 알려야 할 마감
python3 scripts/due.py

# 기준일을 바꿔 확인
python3 scripts/due.py --date 2026-11-10

# 모든 항목의 다음 기한 (대장 점검용)
python3 scripts/due.py --all

# 공휴일 대장 상태
python3 scripts/holidays.py

# 테스트
python3 -m pytest tests/ -v
```

`due.py`는 `data/deadlines.yaml`의 기한일을 `holiday_rule`로 보정한 뒤, `leads`에 걸린 항목만
JSON으로 낸다. **보정된 날짜를 기준으로 D-n을 센다.**

### 시장지표 적재

```bash
# 한 행 추가 (검증에 걸리면 아무것도 쓰지 않고 종료 코드 2)
echo '{"date":"2026-10-09","usdkrw":1352.4,"cgb_3y":2.915,"source":"서울외환시장 종가"}' \
  | python3 scripts/market_append.py

python3 scripts/market_append.py --dry-run --field date=2026-10-09 \
  --field usdkrw=1352.4 --field source="서울외환시장 종가"

# 월간 리뷰 (해석 문장은 --note로 준 것만 들어간다)
python3 scripts/market_report.py --month 2026-09 -o review.html \
  --note "국고채 3년 상승 — 재투자에는 유리, 보유채권 평가손익에는 불리"
```

`columns.yaml`의 `sane_min`/`sane_max`는 **전망치가 아니라 오타 검출용 가드**다. 원/달러를
13.5로, 금리를 bp로 적는 사고를 잡는다. 확인하지 못한 값은 **빈 칸으로 둔다** — `reject_zero`가
켜진 열에 0을 넣으면 거부된다(스왑포인트는 0이 실제 값이라 예외).

### 규제 대장

```bash
python3 scripts/ledger.py add < record.json   # 중복·전이 판정
python3 scripts/ledger.py show <id>           # 그 건이 지금 어디까지 갔나
python3 scripts/ledger.py new-since 2026-10-01
python3 scripts/ledger.py pending             # 시행 예정·기한 임박·시행일 미확인
python3 scripts/ledger.py validate
```

같은 공고가 목록 페이지 번호만 다른 링크로 들어와도 `id`가 같아 중복으로 걸린다(쿼리스트링을
버린다). 상태가 진행하면 새 레코드를 덧붙이고 `supersedes`로 직전을 가리킨다. 뒤로 가는 변경은
`--force`로만 넣고 `corrected`로 표시된다.

## 주의

- `data/deadlines.yaml`의 항목은 현재 **전부 `verified: false`** 다. 1차 출처(법령 원문·감독당국
  서식)로 확인한 뒤 `true`로 올린다. 미검증 항목은 알림에 `미검증` 표시가 붙는다.
- `data/holidays.yaml`은 2026·2027만 수록한다. 범위 밖 날짜를 물으면 `CoverageError`가 난다 —
  조용히 틀린 답을 내놓지 않기 위한 것이다. 매년 11월에 다음 해를 추가한다.
- 회사 실데이터는 올리지 않는다. `CLAUDE.md`의 보안 경계를 지킨다.
- **API 인증키는 저장소에 없다.** 환경 secrets의 `ECOS_API_KEY`·`DATA_GO_KR_KEY`를
  `os.environ`으로만 읽는다.
- ECOS·특일정보 API 호출부는 **아직 없다.** 네트워크가 막혀 응답 형식과 통계표·항목 코드를
  원문으로 확인하지 못했다 — 추측으로 짜지 않고 열린 뒤에 붙인다.
- 월간 리뷰의 인라인 SVG는 아이폰·애플 메일에서는 렌더되지만 일부 클라이언트는 지운다.
  그래서 고·저·평균·전월 대비는 표로도 전부 싣는다.
