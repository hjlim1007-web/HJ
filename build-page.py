#!/usr/bin/env python3
"""baseball.html(아티팩트 본문)을 GitHub Pages용 단독 문서 index.html로 감싼다.

아티팩트는 발행 시점에 <!doctype>/<head>/<body>와 기본 리셋을 자동으로 붙여 주므로
baseball.html에는 그 부분이 없다. Pages에서는 그대로 쓸 수 없어 여기서 같은 골격을 씌운다.
baseball.html을 수정한 뒤 `python3 build-page.py`를 실행하면 index.html이 갱신된다.
"""
import pathlib

DESC = "1~9 중 서로 다른 숫자를 스트라이크·볼 판정만으로 9이닝 안에 맞히는 숫자야구 게임."
SRC = pathlib.Path(__file__).with_name("baseball.html")
OUT = pathlib.Path(__file__).with_name("index.html")

body = SRC.read_text(encoding="utf-8")
head, _, rest = body.partition("</style>")
head += "</style>"

OUT.write_text(f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{DESC}">
<meta name="color-scheme" content="light dark">
<meta property="og:type" content="website">
<meta property="og:title" content="숫자야구 전광판">
<meta property="og:description" content="{DESC}">
<style>
/* 아티팩트 런타임이 붙여 주는 기본 리셋과 동일 */
:root{{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}
body{{margin:0;font:14px system-ui,-apple-system,"Segoe UI",sans-serif}}
img{{max-width:100%}}
[hidden]{{display:none!important}}
</style>
{head}
</head>
<body>
{rest.strip()}
</body>
</html>
""", encoding="utf-8")
print(f"wrote {OUT.name} ({OUT.stat().st_size:,} bytes)")
