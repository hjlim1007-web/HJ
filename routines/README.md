# Routine 정본

Routine 프롬프트는 Routine 설정 안에만 있으면 변경 이력이 남지 않는다. 이 디렉터리를 정본으로
삼고, Routine 설정을 고칠 때 여기도 함께 고친다.

| 파일 | 루틴 이름 | cron | 발송 | trigger id |
|---|---|---|---|---|
| `morning-briefing.md` | 아침 통합 브리핑 — 경제·보험·세무 | `0 23 * * *` UTC = **08:00 KST** | 메일 1통 | `trig_01V94gty1FiT2gGfApxpkT53` |
| `dept-monitoring.md` | 부서별 데일리 모니터링 | `25 23 * * *` UTC = **08:25 KST** | 설정에 따라 1~6통 | `trig_014sDLa1VZYiPpaUHGVc2XFX` |
| `deadline-alert.md` | 마감 D-day 알림 | `CRON_TZ=Asia/Seoul 43 7 * * *` = **07:43 KST** | 걸린 항목이 있는 날만 1통 | `trig_0147RjGRd6CYAxi9gLp24PLz` **(꺼둠)** |
| (계획) `reg-tracker.md` | 규제·제도 원문 추적 | 월요일 **07:47 KST** | 주 1통 | — |
| (계획) `market-monthly.md` | 월간 자금시장 리뷰 | 매월 2일 **08:27 KST** | 월 1통 | — |

좌석 예약 루틴(`trig_012kEjosBYvPntdxTcbponfT`)은 이 저장소와 무관하므로 옮기지 않았다.

## 공통 사양

- 조판: `email-style.md` — 세 메일 루틴이 공유한다. 사양을 루틴마다 복붙하지 않는다.
- 수신: `hjlim1007@naver.com` (부서별 모니터링은 설정 Artifact의 `recipients`를 따른다)
- 발송: Gmail 커넥터의 `send_message`
- 모든 루틴은 무인 실행이다. 사용자에게 질문하지 않는다.

## 저장소와 어긋난 부분 — 동기화 필요

`morning-briefing.md`와 `dept-monitoring.md`는 2026-10-10 기준 Routine 설정의 프롬프트를 옮긴 것이고,
옮기면서 아래를 손봤다. **Routine 설정에는 아직 반영되지 않았다.** 반영하려면
`update_trigger`로 프롬프트를 교체해야 하며, 돌고 있는 자동화를 바꾸는 일이므로 사용자 확인
후에 한다.

- 두 파일 모두: 중복 서술된 HTML 메일 사양을 `email-style.md` 참조로 줄였다.
- `dept-monitoring.md`: 공휴일 판단에 `data/holidays.yaml` / `scripts/due.py`를 먼저 보도록 했다
  (기존에는 웹 검색만). 이번 주 캘린더를 `due.py --all` 출력으로 쓸 수 있게 하고, `verified: false`
  항목에 `미검증`을 붙이도록 했다.

## 마감 알림 루틴 — 켜기 전에 두 가지를 붙여야 한다

`마감 D-day 알림`(`trig_0147RjGRd6CYAxi9gLp24PLz`)은 **현재 꺼져 있다.** 도구(`create_trigger`)로
등록한 루틴이 띄우는 세션에 아래 두 가지가 없어 아무것도 하지 못하기 때문이다. 검증 실행 2회로
확인했다.

| 빠진 것 | 증상 | 결과 |
|---|---|---|
| **소스 저장소** | 세션 태그에 `config:no-git-repo`, `/home/user/HJ`가 없음 | `scripts/due.py`를 돌릴 수 없다 |
| **Gmail 커넥터** | `mcp__Gmail__send_message`가 세션 도구 목록에 없음 | 메일을 보낼 수 없다 |

이 조직에서는 `create_trigger`에 `connectors`를 넘길 수 없고(도구가 거부한다),
`sources`도 넘길 수단이 없다. 세션이 스스로 `add_repo`로 저장소를 붙이는 우회도 시도했으나
그 도구 역시 띄워진 세션에 없었다.

### 붙이는 방법

claude.ai의 **Routines** 화면에서 이 루틴을 열고 두 가지를 설정한다.

1. 소스 저장소에 `hjlim1007-web/HJ`를 추가하고 브랜치를 `claude/elegant-cori-7vpkd8`로 둔다.
   (브랜치를 `main`에 병합한 뒤라면 `main`으로 두어도 된다 — 그때는 루틴 프롬프트 0장의
   브랜치 지정도 함께 지운다.)
2. Gmail 커넥터를 추가한다. `아침 통합 브리핑` 루틴에 Gmail·Claude_Docs·Claude_Code_Remote가
   붙어 있으므로 같은 방식으로 된다.

그 다음 루틴을 켜고, cron을 기다리지 말고 한 번 즉시 실행해 메일 수신과 아이폰 조판을 확인한다.

### 검증 실행에서 확인된 것

실패 상황에서 루틴이 **기한을 손계산으로 지어내지 않고 멈춰 보고했다.** 설계 의도대로다 —
`scripts/due.py` 출력만을 근거로 삼는 규칙이 지켜졌다.

## 알려진 환경 제약

클라우드 세션의 네트워크 정책이 좁으면 `WebFetch`가 DNS 단계에서 실패한다. 그 경우
"기사 원문을 열어 날짜를 확인" 단계가 수행되지 않으므로, 날짜를 오인한 기사가 섞일 수 있다.
허용 도메인에 뉴스 도메인을 넣을지는 결정이 필요하다 (`CLAUDE.md` 환경 제약 참조).
