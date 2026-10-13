# HJ

## 숫자야구 전광판

1~9 중 서로 다른 숫자를 스트라이크·볼 판정만으로 맞히는 웹 게임.

플레이: https://hjlim1007-web.github.io/HJ/

- 3자리는 9이닝, 4자리는 12이닝 안에 맞히면 승리
- 스트라이크(숫자·자리 일치) / 볼(숫자만 일치) / 아웃(전부 불일치)
- 마지막 자리를 입력하면 자동으로 투구
- 지금까지의 판정과 모순되지 않는 남은 정답 후보 수를 매 투구마다 표시
- 서버 없이 브라우저에서만 동작하며, 최소 이닝 기록은 각자 브라우저에 저장된다

### 파일

| 파일 | 용도 |
| --- | --- |
| `baseball.html` | 게임 본문. Claude 아티팩트로 발행하는 원본이라 `<head>`/`<body>` 골격이 없다 |
| `index.html` | 위 파일을 단독 문서로 감싼 GitHub Pages 배포본 (직접 수정하지 않는다) |
| `build-page.py` | `baseball.html` → `index.html` 생성 스크립트 |

`baseball.html`을 고친 뒤에는 `python3 build-page.py`로 `index.html`을 다시 만든다.

### Pages 설정

Settings → Pages → Source: *Deploy from a branch* → Branch: `main` / `(root)`
