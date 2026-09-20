#!/usr/bin/env bash
#
# USB(또는 무선 디버깅)로 연결된 안드로이드 폰에서 Chrome 앱을 실행하고
# 그 안에서 네이버를 연다.
#
#   사용법: ./scripts/open-naver.sh [URL]
#   예시:   ./scripts/open-naver.sh
#           ./scripts/open-naver.sh https://m.naver.com
#
# 사전 준비:
#   1. 폰에서 개발자 옵션 > USB 디버깅 켜기
#   2. PC에 adb 설치 (brew install android-platform-tools / apt install adb)
#   3. 케이블 연결 후 폰에 뜨는 "USB 디버깅 허용" 승인

set -euo pipefail

URL="${1:-https://www.naver.com}"

# 크롬 패키지 후보: 정식판, 베타, 개발자판, 카나리
CHROME_PACKAGES=(
  "com.android.chrome"
  "com.chrome.beta"
  "com.chrome.dev"
  "com.chrome.canary"
)

if ! command -v adb >/dev/null 2>&1; then
  echo "오류: adb 를 찾을 수 없습니다. Android platform-tools 를 설치하세요." >&2
  exit 1
fi

# 연결된 기기 확인 (헤더 줄과 빈 줄 제외, 상태가 device 인 것만)
devices="$(adb devices | awk 'NR>1 && $2=="device" {print $1}')"
if [ -z "$devices" ]; then
  echo "오류: 연결된 안드로이드 기기가 없습니다." >&2
  echo "      'adb devices' 로 상태를 확인하세요 (unauthorized 면 폰에서 디버깅을 허용해야 합니다)." >&2
  exit 1
fi

device_count="$(printf '%s\n' "$devices" | wc -l | tr -d ' ')"
if [ "$device_count" -gt 1 ]; then
  echo "기기가 여러 대 연결되어 있습니다. ANDROID_SERIAL 로 하나를 지정하세요:" >&2
  printf '  %s\n' $devices >&2
  exit 1
fi

serial="$devices"
echo "기기: $serial"

# 설치된 크롬 패키지 찾기
installed_packages="$(adb -s "$serial" shell pm list packages 2>/dev/null | tr -d '\r')"
chrome=""
for pkg in "${CHROME_PACKAGES[@]}"; do
  if printf '%s\n' "$installed_packages" | grep -qx "package:$pkg"; then
    chrome="$pkg"
    break
  fi
done

if [ -z "$chrome" ]; then
  echo "오류: 이 기기에 Chrome 이 설치되어 있지 않습니다." >&2
  exit 1
fi

echo "크롬: $chrome"
echo "여는 중: $URL"

# 폰이 잠겨 있으면 화면을 깨운다 (잠금 해제는 사용자가 직접)
adb -s "$serial" shell input keyevent KEYCODE_WAKEUP >/dev/null 2>&1 || true

# VIEW 인텐트를 크롬 패키지로 못박아 전달
adb -s "$serial" shell am start \
  -a android.intent.action.VIEW \
  -c android.intent.category.BROWSABLE \
  -d "$URL" \
  -p "$chrome" >/dev/null

echo "완료. 폰 화면을 확인하세요."
