# HJ

폰에서 **Chrome 앱을 실행하고 그 안에서 네이버를 여는** 세 가지 구현.

상황에 맞는 것 하나만 쓰면 됩니다.

| 방법 | 쓰는 상황 | 설치 필요 |
|---|---|---|
| [웹 런처](#1-웹-런처-설치-없이-바로) | 폰에서 링크만 열면 됨 | 없음 |
| [안드로이드 앱](#2-안드로이드-앱-홈-화면-아이콘) | 홈 화면 아이콘으로 한 번에 | APK 빌드·설치 |
| [adb 스크립트](#3-adb-스크립트-pc에서-폰-조종) | PC에서 폰을 조종 | adb |

---

## 1. 웹 런처 (설치 없이 바로)

`web/index.html` — 버튼을 누르면 크롬 앱으로 전환한 뒤 네이버를 엽니다.

- **Android** — `intent://` 스킴에 `package=com.android.chrome` 을 박아 크롬을 지정해 호출합니다.
  크롬이 없으면 `S.browser_fallback_url` 로 기본 브라우저가 대신 엽니다.
- **iOS** — 크롬 앱의 커스텀 스킴 `googlechromes://` 로 전환하고,
  1.4초 안에 전환이 안 되면 크롬 미설치로 보고 기본 브라우저로 폴백합니다.
- **PC** — 웹페이지에서 특정 브라우저를 강제 실행할 방법은 없습니다. 새 탭으로만 엽니다.

### 쓰는 법

셋 중 아무거나:

- **GitHub Pages** — 저장소 Settings → Pages 에서 이 브랜치의 `/web` 을 소스로 지정하면
  `https://<사용자명>.github.io/hj/` 를 폰에서 열 수 있습니다.
- **파일로** — `web/index.html` 을 폰에 내려받아 파일 앱에서 엽니다.
- **로컬 서버** — 같은 와이파이에 있는 PC에서 `python3 -m http.server 8000 -d web` 후
  폰 브라우저로 `http://<PC의_IP>:8000` 접속.

> 주의: `intent://` 와 `googlechromes://` 는 **폰의 실제 브라우저**에서 열어야 동작합니다.
> 카카오톡·인스타그램 같은 앱 내장 브라우저나 iframe 안에서는 커스텀 스킴이 차단될 수 있습니다.

---

## 2. 안드로이드 앱 (홈 화면 아이콘)

`android/` — 아이콘을 누르면 화면을 그리지 않고 곧장 크롬으로 네이버를 연 뒤 스스로 종료하는
투명 액티비티 한 개짜리 앱입니다.

핵심은 `MainActivity.kt` 의 이 부분입니다.

```kotlin
val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://www.naver.com")).apply {
    setPackage("com.android.chrome")          // 크롬으로 못박기
    addCategory(Intent.CATEGORY_BROWSABLE)
    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
}
startActivity(intent)
```

두 가지를 챙겨야 실기기에서 동작합니다.

- **패키지 가시성** — Android 11(API 30)부터 다른 앱이 기본적으로 보이지 않습니다.
  `AndroidManifest.xml` 의 `<queries>` 에 크롬 패키지를 선언해야 조회·호출이 됩니다.
- **폴백** — 크롬이 없거나 비활성화된 기기에서는 패키지를 지정하지 않은 VIEW 인텐트로
  떨어뜨려 기본 브라우저가 열도록 했습니다. 정식판이 없으면 베타/개발자판/카나리도 찾습니다.

### 빌드

Android Studio 로 `android/` 폴더를 열고 Run 하면 됩니다. 커맨드라인이라면:

```bash
cd android
gradle wrapper          # gradlew 가 없으므로 한 번만 생성 (Gradle 8.7+ 필요)
./gradlew installDebug  # 연결된 기기에 바로 설치
```

---

## 3. adb 스크립트 (PC에서 폰 조종)

`scripts/open-naver.sh` — USB/무선 디버깅으로 연결된 폰의 크롬을 열고 네이버를 띄웁니다.

```bash
./scripts/open-naver.sh                     # https://www.naver.com
./scripts/open-naver.sh https://m.naver.com # 주소 지정
```

설치된 크롬 패키지를 먼저 확인하고, 화면을 깨운 뒤 VIEW 인텐트를 크롬으로 보냅니다.
사전 준비는 폰의 개발자 옵션 > USB 디버깅 활성화와 PC의 adb 설치입니다.

실제로 실행되는 명령은 한 줄입니다.

```bash
adb shell am start -a android.intent.action.VIEW \
  -c android.intent.category.BROWSABLE \
  -d https://www.naver.com -p com.android.chrome
```
