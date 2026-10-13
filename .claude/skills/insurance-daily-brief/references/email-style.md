# HTML 메일 조판 — Chubb 스타일, 모바일 우선

두 메일(아침 브리핑 / 부서별 모니터링)이 같은 조판을 쓴다. 머리말 제목만 다르다.

디자인 기준은 Chubb의 기업 브랜드 언어다 — 흰 배경, 큰 제목, 넉넉한 여백, 머리카락 굵기의 가로선. 카드를 회색 박스로 감싸는 대시보드풍이 아니라 **편집물(editorial) 지면**처럼 짠다. 서체만은 브랜드 서체(Publico/Georgia 계열) 대신 고딕을 쓴다 — 아래 설명 참조.

## 모바일 우선 — 가장 중요하다

수신자는 아이폰 메일로 읽는다. **고정폭을 쓰면 메일 앱이 지면 전체를 축소해 띄우기 때문에 글자가 읽을 수 없게 작아진다.** 실제로 680px 고정폭 때문에 13.5px 본문이 7px쯤으로 렌더링된 일이 있었다. 그래서:

- `<table width="680">` 같은 **고정폭 속성을 쓰지 않는다.** 바깥 표는 `width="100%"`, 안쪽 본문 표는 `width="100%"` + `style="max-width:680px"`. 데스크톱에서 680px에서 멈추고 좁은 화면에서는 화면 폭을 따라간다.
- 안쪽 표·셀에 px 고정폭을 주지 않는다. 폭이 필요한 칸(번호, 세로선, 시각)만 20~62px.
- **좌우 여백은 24px.** 40px은 375px 화면에서 본문을 너무 좁게 만든다.
- **3열 표를 쓰지 않는다.** 지표·환율 표는 2열(왼쪽 항목명 + 그 아래 비고, 오른쪽 숫자). 일정 표는 시각(62px) + 내용.
- 숫자 칸에 `white-space:nowrap` — 금액·금리가 줄바꿈되지 않게.
- 본문 컨테이너에 `word-break:keep-all` — 한국어 단어가 중간에 잘리지 않게.
- 본문 `line-height:1.7`, 표 행 상하 패딩 11px 이상.
- **미디어 쿼리에 기대지 않는다**(네이버 메일 등에서 제거된다). 미디어 쿼리 없이 375px에서 읽혀야 한다.
- 모든 스타일은 인라인 `style` 속성. 웹폰트·외부 CSS·스크립트·다크모드 미디어쿼리를 쓰지 않는다. 레이아웃은 `<table>` 기반(네이버 메일·아웃룩 호환).

## 타이포그래피

- **고딕(sans-serif)을 쓴다.** `-apple-system, BlinkMacSystemFont, 'Malgun Gothic', 'Apple SD Gothic Neo', '맑은 고딕', sans-serif`. 세리프를 쓰지 않는다 — Georgia는 한글 글리프가 없어 윈도우에서 바탕체로 떨어지고, 작은 라벨만 고딕으로 남아 한 지면에 두 서체가 섞인다. 수신자가 그 렌더링을 싫어한다.
- **크기 4종만** (브랜드 매뉴얼 규칙): 제목 28px / 섹션·기사 제목 19px / 본문 **16px** / 라벨·각주 13~14px.
- **본문은 16px 아래로 내리지 않는다.** 13px은 표의 보조 설명과 작은 라벨에만.
- **전부 대문자 라벨을 쓰지 않는다**(`text-transform:uppercase`, `DAILY BRIEFING` 식). 브랜드 매뉴얼이 금지한다.
- **본문 강조에 굵게를 쓰지 않는다.** 다만 세리프가 빠진 만큼 위계를 받칠 것이 필요하므로 **제목에만 `font-weight:600`**을 허용한다. 본문·표·라벨은 기본 굵기로 두고 강조는 색과 여백으로 만든다.

## 색

| 용도 | 값 |
|---|---|
| 배경 | `#ffffff` (회색 배경 금지) |
| 연한 밴드 | `#f7f7f7` |
| 제목 | `#212529` |
| 본문 | `#3a3f44` |
| 보조 | `#8a8f94` |
| 머리카락 선 | `#e3e3e3` |
| 구분선 | `#c9c9c9` |
| 포인트(청록, Chubb 로고색) | `#01c1d6` |
| 강조·상승 | `#150f96` |
| 하락·안정 | `#0e7c86` |

## 구성 순서

1. 상단 `#212529` 6px 가로 밴드 → 흰 지면에 제목(28px, 600) → 날짜·조사 범위·수신 기준을 14px 보조색으로 `<br>`로 2~3줄 끊어서. 로고나 회사 마크는 넣지 않는다.
2. "오늘의 핵심 5줄" — 회색 박스 없이 왼쪽에 3px `#01c1d6` 세로선만. 번호는 청록 숫자로 작게.
3. 섹션 머리 — 위에 `#c9c9c9` 1px 선 + 청록 숫자 + 섹션명(19px, 600). 건수 표기는 넣지 않는다(좁은 화면에서 제목을 밀어낸다). 섹션이 빠진 날은 번호를 1부터 빈틈 없이 다시 매긴다.
4. 표 — **격자 테두리를 쓰지 않는다.** 행마다 아래쪽 `#e3e3e3` 1px 선만, 머리행은 13px 보조색 + 아래 `#c9c9c9` 선. 숫자 우측 정렬. 상승 `▲ #150f96`, 하락 `▼ #0e7c86`. 환율 표의 원/달러 행은 배경 `#f7f7f7`로 눌러 표시(굵게 대신).
5. 기사 카드 — 박스로 감싸지 않고 사이를 `#e3e3e3` 1px 선으로만 나눈다. 태그는 칩 대신 13px 청록 글자를 가운뎃점으로. 제목 19px `#212529` 600. 실무 시사점은 `#f7f7f7` 밴드에 청록 라벨과 함께. **가장 중요한 기사 1건만** 왼쪽에 3px `#150f96` 세로선.
6. 출처는 카드 하단 14px, 링크 `#01c1d6` 밑줄 없음, `line-height:2`로 터치 간격.
7. 뉴스가 없는 섹션은 16px 보조색 한 줄 `특이사항 없음 — (사유)`.
8. 캘린더는 청록 사각 글머리(`&#9633;`) + 본문 목록.
9. 맨 아래 `#c9c9c9` 선 아래 14px 보조색 각주 — 조사 범위, "동일 사안의 중복 보도는 1건으로 통합".
10. **부서 섹션**은 앞에 `#212529` 2px 선과 `부서 섹션` 머리를 두어 ①②③과 층을 나누고, 각 부서 블록 왼쪽에 3px `#01c1d6` 세로선.

섹션 간 위아래 패딩 24px 이상.

## 코드 패턴

### 바깥 골격

```html
<div style="margin:0;padding:0;background-color:#ffffff;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;background-color:#ffffff;">
<tr><td align="center" style="padding:0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:680px;font-family:-apple-system,BlinkMacSystemFont,'Malgun Gothic','Apple SD Gothic Neo','맑은 고딕',sans-serif;word-break:keep-all;">
<tr><td style="background-color:#212529;height:6px;line-height:6px;font-size:0;">&nbsp;</td></tr>
<!-- 내용 -->
</table>
</td></tr></table>
</div>
```

### 머리말

```html
<tr><td style="padding:30px 24px 0 24px;">
<div style="font-size:28px;font-weight:600;color:#212529;line-height:1.3;letter-spacing:-0.4px;">아침 브리핑</div>
<div style="font-size:14px;color:#8a8f94;padding-top:10px;line-height:1.6;">2026년 10월 13일 화요일<br>조사 범위 10-12 00:00 → 10-13 08:00 KST<br>중소 생명보험사 재무회계팀 · 자금팀 기준</div>
</td></tr>
```

### 섹션 머리

```html
<tr><td style="padding:32px 24px 0 24px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid #c9c9c9;">
<tr><td style="padding:14px 0 0 0;"><span style="color:#01c1d6;font-size:19px;font-weight:600;">1</span><span style="font-size:19px;font-weight:600;color:#212529;padding-left:10px;">시장 지표와 오늘 일정</span></td></tr></table>
```

### 2열 지표 행 — 이 패턴을 지킨다

```html
<tr><td style="border-bottom:1px solid #e3e3e3;padding:11px 0;">
  <div style="font-size:16px;color:#3a3f44;line-height:1.4;">국고채 3년</div>
  <div style="font-size:13px;color:#0e7c86;padding-top:3px;line-height:1.5;">▼ 6.2bp</div>
</td><td align="right" valign="top" style="border-bottom:1px solid #e3e3e3;padding:11px 0;font-size:16px;color:#3a3f44;white-space:nowrap;">3.921%</td></tr>
```

원/달러 행처럼 눌러 표시할 때는 `<tr style="background-color:#f7f7f7;">`에 좌우 패딩 10px을 더한다.

### 기사 카드

```html
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:26px;border-top:1px solid #e3e3e3;"><tr><td style="padding:22px 0 0 0;">
<div style="font-size:13px;color:#01c1d6;">감독 · 수수료 · 10월 8일</div>
<div style="font-size:19px;font-weight:600;color:#212529;padding:8px 0;line-height:1.45;">제목</div>
<div style="font-size:16px;color:#3a3f44;line-height:1.7;">본문 한두 문장.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;background-color:#f7f7f7;margin-top:14px;"><tr><td style="padding:15px 16px;font-size:16px;color:#3a3f44;line-height:1.7;"><span style="font-size:13px;color:#01c1d6;">실무 시사점</span><br>…</td></tr></table>
<div style="font-size:14px;color:#8a8f94;padding-top:12px;line-height:2;">출처 <a href="…" style="color:#01c1d6;text-decoration:none;">보험저널</a></div>
</td></tr></table>
```

가장 중요한 기사 1건은 카드를 2열로 감싸 왼쪽에 세로선을 둔다.

```html
<tr><td width="3" style="width:3px;background-color:#150f96;font-size:0;line-height:0;">&nbsp;</td><td style="padding:0 0 0 16px;">
```

부서 블록은 같은 패턴에 `#01c1d6`을 쓴다.

## 플레인텍스트 본문

`send_message`에 `body`(플레인텍스트)와 `htmlBody`를 함께 넣는다. 플레인텍스트는 마크다운 기호 없이 쓴다 — 표는 `- 항목 값` 목록으로, 섹션은 번호와 제목 줄로. 서식을 끈 환경에서도 읽히게 하는 용도다.

## 조판 확인용으로 보여줄 때

메일을 보내기 전에 조판을 보고 싶다는 요청이면, 메일 HTML을 그대로 감싼 확인용 지면을 아티팩트로 발행한다. 머리에 받는 사람·제목·발송 여부·조사 창·조판 요약을 메타데이터로 올리고, 그 아래 `.frame`에 메일 HTML을 넣는다. 고정폭이 없으므로 그 지면도 화면 폭을 따라가 휴대폰에서 실제 메일과 같게 보인다.
