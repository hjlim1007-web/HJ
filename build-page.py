#!/usr/bin/env python3
"""baseball.html(아티팩트 본문)을 GitHub Pages용 단독 문서 index.html로 감싼다.

아티팩트는 발행 시점에 <!doctype>/<head>/<body>와 기본 리셋을 자동으로 붙여 주므로
baseball.html에는 그 부분이 없다. Pages에서는 그대로 쓸 수 없어 여기서 같은 골격을 씌운다.
baseball.html을 수정한 뒤 `python3 build-page.py`를 실행하면 index.html이 갱신된다.
"""
import pathlib

PAGES = [
    ("baseball.html", "index.html", "숫자야구 전광판",
     "1~9 중 서로 다른 숫자를 스트라이크·볼 판정만으로 9이닝 안에 맞히는 숫자야구 게임."),
    ("lightsout.html", "lights-out.html", "라이트 아웃",
     "한 칸을 누르면 상하좌우가 함께 뒤집히는 전구판을 모두 끄는 논리 퍼즐. 남은 최소 클릭 수를 실시간으로 계산한다."),
]


def build(src_name, out_name, title, desc):
    src = pathlib.Path(__file__).with_name(src_name)
    out = pathlib.Path(__file__).with_name(out_name)
    body = src.read_text(encoding="utf-8")
    head, _, rest = body.partition("</style>")
    head += "</style>"
    out.write_text(f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{desc}">
<meta name="color-scheme" content="light dark">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
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
    print(f"wrote {out.name} ({out.stat().st_size:,} bytes)")


for args in PAGES:
    build(*args)
