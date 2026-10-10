# 마감 D-day 알림 (매일 07:43 KST)

cron: `CRON_TZ=Asia/Seoul 43 7 * * *`
무인 실행이다. 사용자에게 질문하지 말고 바로 처리한다.

이 알림의 생명은 **소음이 없는 것**이다. 걸린 항목이 없으면 메일도 푸시도 보내지 않는다.
매일 오는 알림은 읽히지 않는다.

## 0. 저장소 준비

루틴이 띄우는 세션에는 **저장소가 붙어 있지 않다.** 직접 가져와야 한다.

1. `mcp__claude-code-remote__add_repo`를 `owner: "hjlim1007-web"`, `repo: "HJ"`로 호출한다.
   (도구가 목록에 없으면 `ToolSearch`로 `select:mcp__claude-code-remote__add_repo`를 불러온다.)
   **먼저 curl이나 `gh repo view`로 저장소 존재를 확인하지 않는다** — 비공개 저장소는 404가 떠서
   도구를 건너뛰게 만든다. 바로 호출하고 결과를 본다.
2. 결과가 주는 clone 명령으로 `/home/user/HJ`에 가져온다. 브랜치를 지정한다.

   ```bash
   git clone -b claude/elegant-cori-7vpkd8 <결과가 준 URL> /home/user/HJ
   ```
3. 이미 `/home/user/HJ`가 있으면 클론하지 않고 브랜치만 맞춘다.

   ```bash
   cd /home/user/HJ && git fetch origin claude/elegant-cori-7vpkd8 \
     && git checkout claude/elegant-cori-7vpkd8 && git pull origin claude/elegant-cori-7vpkd8
   ```

네트워크 오류로 실패하면 2초·4초·8초·16초 간격으로 최대 4회 다시 시도한다. 그래도 저장소를
가져오지 못하면 **그 사실만 보고하고 종료한다.** 기한을 기억이나 손계산으로 만들어 보내지 않는다.

## 1. 산출

```bash
cd /home/user/HJ && python3 scripts/due.py
```

출력 JSON이 이 메일의 **유일한 근거**다. `alerts`에 없는 기한을 기억이나 추측으로 추가하지 않고,
있는 항목을 임의로 빼지도 않는다. 스크립트가 실패하면 그 사실과 오류 내용만 보고하고 종료한다
— 손으로 계산해 대신 보내지 않는다.

`calendar.years`에 **올해와 다음 해가 모두 들어있는지** 확인한다. 올해가 마지막 수록 연도이면
메일 각주에 "공휴일 대장에 다음 해가 없다 — `data/holidays.yaml` 갱신 필요"를 한 줄 넣는다.
`CoverageError`가 나면 그것이 원인이므로 오류를 그대로 보고한다.

## 2. 발송 여부

- `alert_count`가 **0이면 메일을 보내지 않는다.** 채팅 답변에 `오늘 걸린 마감 없음 (기준일 YYYY-MM-DD)`
  한 줄만 남기고 끝낸다.
- 1 이상이면 메일 1통을 `hjlim1007@naver.com`으로 보낸다. Gmail의 `send_message` 도구를 쓴다.
- 발송이 실패하면 오류 내용을 채팅 답변 맨 끝에 한 줄로 밝힌다. 다른 방법으로 우회 발송하지 않는다.

## 3. 메일 구성

조판은 **스크립트가 한다.** 매일 LLM이 HTML을 새로 만들면 날마다 결과가 흔들리므로,
`scripts/render_alert.py`가 `due.py` 출력을 받아 고정된 조판으로 HTML을 낸다.

```bash
cd /home/user/HJ && python3 scripts/due.py > /tmp/due.json
python3 scripts/render_alert.py < /tmp/due.json -o /tmp/alert.html
```

- 표준 오류로 `SUBJECT: [마감] YYYY-MM-DD(요일) D-n 항목 N건` 한 줄이 나온다. **그 제목을 그대로
  메일 제목으로 쓴다.** 가장 급한 항목의 D-n이 들어가므로 당일 건이 있으면 D-0으로 나타난다.
- 걸린 항목이 없으면 HTML을 내지 않고 **종료 코드 3**으로 끝낸다 — 그 날은 메일을 보내지 않는다.
- `/tmp/alert.html` 전문을 그대로 메일 본문(HTML)으로 보낸다. **손으로 고치지 않는다.**
- 스크립트가 0도 3도 아닌 코드로 끝나면 오류 내용만 보고하고 종료한다.

조판 사양은 `routines/email-style.md`이며 `render_alert.py`가 그것을 구현한 것이다. 사양을
바꾸려면 스크립트를 고치고 테스트를 돌린다. 메일을 만들 때마다 다르게 조판하지 않는다.

스크립트가 쓰는 값은 전부 `due.py` JSON에서 온다. 참고로 각 항목이 어떻게 들어가는지:

- `name` — 제목 (19px, 600)
- `due_date`와 `days_until` → `D-3 · 2026-11-10(화)` 형태. `shifted`가 true면
  `(원래 2026-11-08, 휴일 보정)`을 13px 보조색으로 덧붙인다. **보정됐다는 사실 자체가 정보다.**
- `basis` — 근거. 본문 16px.
- `note` — 있으면 본문에 잇는다. 없으면 생략한다.
- `verified`가 false면 제목 옆에 13px 청록으로 `미검증`을 붙이고, 각주에
  "미검증 항목은 1차 출처로 확인되지 않은 기한이다 — 실제 기한을 확인하고 쓸 것"을 한 줄 넣는다.
- `source` — 있으면 14px 링크로.

정렬은 JSON 순서(기한일 → 분류 → id) 그대로 둔다. D-0 항목이 있으면 그 블록만 왼쪽에 3px
`#150f96` 세로선을 둔다.

분류(`category`)가 2개 이상이면 분류별로 묶어 소제목(19px)을 둔다. 1개면 묶지 않는다.

## 4. 하지 않을 것

- 기한 날짜를 스크립트 출력과 다르게 쓰지 않는다.
- JSON에 없는 기한을 "이것도 곧이다"라며 추가하지 않는다. 대장에 없는 기한이 떠오르면 메일에
  넣는 대신 채팅 답변에 "`data/deadlines.yaml`에 추가 검토: …"로 적어 사용자가 판단하게 한다.
- 금액·거래상대·내부 조직명을 메일에 넣지 않는다 (`CLAUDE.md` 보안 경계).
- 저장소에 커밋하지 않는다. 이 루틴은 읽기만 한다.
