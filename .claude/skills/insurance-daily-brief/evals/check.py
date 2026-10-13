#!/usr/bin/env python3
"""Programmatic assertion checks for the insurance-daily-brief skill evals.

Reads a run directory (…/with_skill or …/without_skill), inspects its
outputs/, and writes grading.json next to the outputs.
"""
import json, os, re, sys

PALETTE = {"#ffffff","#f7f7f7","#212529","#3a3f44","#8a8f94","#e3e3e3",
           "#c9c9c9","#01c1d6","#150f96","#0e7c86","#fff"}
DEPTS = ["재무회계","자금","계리","상품","수당","Risk Management","일반계정운용","특별계정운용"]

def result(text, passed, evidence):
    return {"text": text, "passed": bool(passed), "evidence": evidence[:400]}

def check(run_dir, kind):
    out = os.path.join(run_dir, "outputs")
    html = ""
    html_path = None
    for name in ("brief.html", "email.html", "index.html"):
        p = os.path.join(out, name)
        if os.path.exists(p):
            html_path, html = p, open(p, encoding="utf-8").read()
            break
    text = html
    for extra in ("brief.md", "answer.md", "notes.md"):
        p = os.path.join(out, extra)
        if os.path.exists(p):
            text += "\n" + open(p, encoding="utf-8").read()

    r = []
    if not html:
        files = os.listdir(out) if os.path.isdir(out) else []
        r.append(result("메일 HTML을 산출했다", False, f"brief.html 없음. 디렉터리 내용: {files}"))
        return r
    r.append(result("메일 HTML을 산출했다", True, f"{os.path.basename(html_path)} {len(html)}바이트"))

    # --- 조판: 모바일 유동폭 ---
    fixed = re.findall(r'width="(\d{3,})"', html)
    bad_fixed = [w for w in fixed if int(w) > 100]
    has_max = "max-width:680px" in html.replace(" ", "")
    r.append(result("고정폭 속성 없이 유동폭(max-width:680px)으로 짰다",
                    not bad_fixed and has_max,
                    f'width="…" 고정값 {bad_fixed or "없음"} · max-width:680px {"있음" if has_max else "없음"}'))

    # --- 본문 16px 이상 (13·14px은 라벨용으로 허용) ---
    sizes = sorted({int(m) for m in re.findall(r'font-size:\s*(\d+)(?:\.\d+)?px', html)})
    too_small = [s for s in sizes if s < 13 or s == 15]
    r.append(result("본문을 16px 아래로 내리지 않았다 (라벨 13~14px만 허용)",
                    not too_small and 16 in sizes,
                    f"쓰인 크기 {sizes} · 위반 {too_small or '없음'}"))

    # --- 서체 ---
    gothic = "Malgun Gothic" in html or "Apple SD Gothic Neo" in html
    serif = re.search(r"Georgia|serif(?!-)|바탕|Batang|명조", html) and "sans-serif" not in html
    r.append(result("고딕 서체 스택을 쓰고 세리프를 쓰지 않았다",
                    gothic and not serif,
                    f'고딕 스택 {"있음" if gothic else "없음"} · 세리프 {"발견" if serif else "없음"}'))

    # --- 메일 호환성 ---
    r.append(result("미디어 쿼리·웹폰트·스크립트를 쓰지 않았다",
                    "@media" not in html and "<script" not in html and "fonts.googleapis" not in html,
                    f'@media {"있음" if "@media" in html else "없음"} · script {"있음" if "<script" in html else "없음"}'))
    r.append(result("word-break:keep-all로 한글 단어 잘림을 막았다",
                    "word-break:keep-all" in html.replace(" ", ""),
                    "있음" if "word-break:keep-all" in html.replace(" ", "") else "없음"))
    r.append(result("숫자 칸에 white-space:nowrap을 줬다",
                    "white-space:nowrap" in html.replace(" ", ""),
                    "있음" if "white-space:nowrap" in html.replace(" ", "") else "없음"))
    r.append(result("좌우 여백 24px을 썼다",
                    re.search(r'padding:[^";]*\b24px', html) is not None,
                    (re.search(r'padding:[^";]*\b24px[^";]*', html).group(0) if re.search(r'padding:[^";]*\b24px', html) else "없음")))

    # --- 색 팔레트 ---
    hexes = {h.lower() for h in re.findall(r'#[0-9a-fA-F]{3,6}', html)}
    off = sorted(hexes - PALETTE)
    r.append(result("지정 팔레트 안의 색만 썼다", not off, f"팔레트 외 {off or '없음'}"))

    # --- 내용 품질 ---
    r.append(result('시사점을 "모니터링이 필요하다"로 끝내지 않았다',
                    "모니터링이 필요" not in text,
                    "발견" if "모니터링이 필요" in text else "없음"))

    if kind in ("dept", "weekend"):
        missing = [d for d in DEPTS if d not in html]
        r.append(result("설정에서 켜진 8개 부서가 모두 섹션으로 들어갔다",
                        not missing, f"누락 {missing or '없음'}"))
        r.append(result("부서 블록에 3px #01c1d6 좌측 괘선을 뒀다",
                        re.search(r'width:3px;background-color:#01c1d6', html.replace(" ", "")) is not None,
                        "있음" if re.search(r'width:3px;background-color:#01c1d6', html.replace(" ", "")) else "없음"))
        r.append(result("여러 부서에 걸린 기사를 (… 각도) 표시로 교차참조했다",
                        "각도)" in html, "있음" if "각도)" in html else "없음"))

    if kind == "morning":
        fx = all(p in html for p in ("원 / 달러", "원/달러")) or "원/달러" in html or "원 / 달러" in html
        pairs = [p for p in ("달러", "유로", "엔") if p in html]
        has_100yen = "100엔" in html
        r.append(result("환율표에 원/달러·원/유로·원/엔(100엔당)을 모두 넣었다",
                        len(pairs) == 3 and has_100yen,
                        f"통화 {pairs} · 100엔 표기 {'있음' if has_100yen else '없음'}"))
        r.append(result("'오늘의 핵심 5줄'을 넣었다", "핵심" in html and "5줄" in html,
                        "있음" if ("핵심" in html and "5줄" in html) else "없음"))
        order_keys = ["시장 지표", "거시", "세"]
        pos = [html.find(k) for k in order_keys]
        r.append(result("섹션 순서가 지표 → 거시 → … → 세무다",
                        all(p > -1 for p in pos) and pos == sorted(pos), f"위치 {pos}"))

    if kind == "weekend":
        window_ok = ("10-16" in text or "10월 16" in text or "직전 영업일" in text)
        is_24h = re.search(r"최근\s*24\s*시간", text) is not None
        r.append(result("토요일 회차 조사 창을 직전 영업일(10/16 금) 이후로 넓혔다",
                        window_ok and not is_24h,
                        f"직전영업일 근거 {'있음' if window_ok else '없음'} · 24시간 창 {'씀' if is_24h else '안씀'}"))
    return r

if __name__ == "__main__":
    run_dir, kind = sys.argv[1], sys.argv[2]
    res = check(run_dir, kind)
    grading = {"expectations": res,
               "passed": sum(1 for x in res if x["passed"]),
               "total": len(res)}
    with open(os.path.join(run_dir, "grading.json"), "w", encoding="utf-8") as f:
        json.dump(grading, f, ensure_ascii=False, indent=2)
    print(f'{run_dir.split("iteration-1/")[-1]}: {grading["passed"]}/{grading["total"]}')
