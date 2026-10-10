# HJ

중소 생명보험사 재무회계팀/자금팀 업무 자동화. 규칙과 보안 경계는 `CLAUDE.md`를 먼저 읽는다.

## 무엇이 있는가

| 디렉터리 | 내용 |
|---|---|
| `routines/` | Routine 프롬프트의 정본. 루틴 ↔ trigger id 대조표는 `routines/README.md` |
| `data/deadlines.yaml` | 마감 기한 규칙 (세무·감독보고·결산). 근거 조문과 `verified` 플래그 포함 |
| `data/holidays.yaml` | 공휴일·대체공휴일·근로자의 날 (2026·2027) |
| `data/market/` | 시장지표 시계열 (예정) |
| `data/regulations/` | 규제 변경 대장 (예정) |
| `scripts/` | 순수 계산 스크립트. 네트워크를 타지 않는다 |
| `tests/` | `python3 -m pytest tests/ -v` |

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

## 주의

- `data/deadlines.yaml`의 항목은 현재 **전부 `verified: false`** 다. 1차 출처(법령 원문·감독당국
  서식)로 확인한 뒤 `true`로 올린다. 미검증 항목은 알림에 `미검증` 표시가 붙는다.
- `data/holidays.yaml`은 2026·2027만 수록한다. 범위 밖 날짜를 물으면 `CoverageError`가 난다 —
  조용히 틀린 답을 내놓지 않기 위한 것이다. 매년 11월에 다음 해를 추가한다.
- 회사 실데이터는 올리지 않는다. `CLAUDE.md`의 보안 경계를 지킨다.
