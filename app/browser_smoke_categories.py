"""Real-browser check of V1.2 segment-aware category filtering (Playwright + Chromium, not part of requirements.txt).

    python -m app.browser_smoke_categories [--out docs/demo_screenshots] [--fixture-data]

For EVERY TRAIN segment, in English and in Turkish, the options of the "Garment category" dropdown are read from the page and
compared with the categories that have at least one eligible TRAIN template in that segment. The expected lists are computed at
run time from the same processed folder (`load_app_data(...).available_categories`), never typed in. Also checked: no
"(no TRAIN templates)" entry, a category that disappears is replaced and one that stays valid is kept, an empty segment (if the
data has one) disables generation, a result generated before a segment change is labelled as belonging to the previous
request, a language switch does not regenerate, and there are no browser console errors.

`--fixture-data` uses the SYNTHETIC category fixture (app/tests/category_fixtures.py); without it the real processed data
(or CAGO_PROCESSED_DIR) is used. Exit code 0 = all checks passed.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.adapters import DEFAULT_PROCESSED_DIR, load_app_data  # noqa: E402
from app.browser_smoke import free_port, wait_http  # noqa: E402
from app.browser_smoke_i18n import choose, launch, selected, write_fixture_data  # noqa: E402
from app.i18n import get_translator  # noqa: E402
from app.state import resolve_category  # noqa: E402

LABELS = {"en": ("Segment", "Garment category", "Generate recommendations"), "tr": ("Hedef grup", "Giysi kategorisi", "Önerileri üret")}


def dropdown_options(pg, label: str) -> list[str]:
    box = pg.locator(f'input[aria-label="{label}"]').first
    box.click()
    pg.wait_for_timeout(400)
    opts = [o.inner_text().strip() for o in pg.get_by_role("option").all()]
    return opts


def close_dropdown(pg) -> None:
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "demo_screenshots"))
    ap.add_argument("--fixture-data", action="store_true", help="use the SYNTHETIC category fixture instead of the processed data")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    tmp = tempfile.TemporaryDirectory()
    env = {**os.environ, "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false"}
    data_dir = Path(os.environ.get("CAGO_PROCESSED_DIR", DEFAULT_PROCESSED_DIR))
    if args.fixture_data:
        data_dir = write_fixture_data(Path(tmp.name))
        env["CAGO_PROCESSED_DIR"] = str(data_dir)
    data = load_app_data(data_dir)                      # the same TRAIN-only loader the app uses
    segments = data.segments()
    expected = {s: data.available_categories(s) for s in segments}
    evidence: dict = {"data": "SYNTHETIC category fixture" if args.fixture_data else f"processed data in {data_dir}",
                      "available_categories": expected,
                      "eligible_templates": {s: {c: data.eligible_templates(s, c) for c in cats} for s, cats in expected.items()}}
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"), "--server.headless", "true",
                             "--server.port", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    checks: list[tuple[str, bool]] = []
    console_errors: list[str] = []
    try:
        url = f"http://localhost:{port}"
        wait_http(url + "/_stcore/health")
        with sync_playwright() as p:
            br = launch(p)
            pg = br.new_page(viewport={"width": 1500, "height": 1800})
            pg.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))

            def settle():
                pg.wait_for_timeout(700)
                pg.wait_for_function("() => !document.body.innerText.includes('Running...')", timeout=120_000)
                pg.wait_for_timeout(900)

            pg.goto(url)
            pg.get_by_text("Generate recommendations").first.wait_for(timeout=120_000)
            settle()
            for lang in ("en", "tr"):
                tr = get_translator(lang)
                seg_label, cat_label, gen_label = LABELS[lang]
                if lang == "tr":
                    pg.get_by_role("radio", name="TR", exact=True).first.click()
                    settle()
                for seg in segments:
                    choose(pg, seg_label, tr.label("segment", seg))
                    settle()
                    want = [tr.option_labels("category", expected[seg])[c] for c in expected[seg]]
                    if not expected[seg]:
                        body = pg.inner_text("body")
                        ok = (pg.locator(f'input[aria-label="{cat_label}"]').count() == 0 and tr.t("form.no_categories") in body
                              and pg.get_by_role("button", name=gen_label).first.is_disabled())
                        checks.append((f"{lang}: {seg} has no available category -> message, generation disabled", ok))
                        continue
                    got = dropdown_options(pg, cat_label)
                    if seg == "men" or seg == segments[-1]:
                        pg.screenshot(path=str(out / f"categories_{lang}_{seg}.png"))
                    close_dropdown(pg)
                    evidence.setdefault("observed_options", {}).setdefault(lang, {})[seg] = got
                    checks.append((f"{lang}: {seg} offers exactly the {len(want)} available categories", got == want))
                    checks.append((f"{lang}: {seg} shows no '(no TRAIN templates)' entry",
                                   not any("TRAIN templates" in o or "TRAIN şablonu yok" in o for o in got)))

            # replacement / preservation when the segment changes (EN)
            pg.get_by_role("radio", name="EN", exact=True).first.click()
            settle()
            tr = get_translator("en")
            pair = next(((a, b, c) for a in segments for b in segments if a != b for c in expected[a] if c not in expected[b]
                         and expected[b]), None)
            if pair:
                a, b, c = pair
                choose(pg, "Segment", tr.label("segment", a))
                settle()
                choose(pg, "Garment category", tr.label("category", c))
                settle()
                choose(pg, "Segment", tr.label("segment", b))
                settle()
                want = tr.label("category", resolve_category(expected[b], c))
                checks.append((f"{c} disappears when {a} -> {b}: replaced by {want}", selected(pg, "Garment category") == want))
            keep = next(((a, b, c) for a in segments for b in segments if a != b for c in expected[a] if c in expected[b]), None)
            if keep:
                a, b, c = keep
                choose(pg, "Segment", tr.label("segment", a))
                settle()
                choose(pg, "Garment category", tr.label("category", c))
                settle()
                choose(pg, "Segment", tr.label("segment", b))
                settle()
                checks.append((f"{c} stays selected when {a} -> {b}", selected(pg, "Garment category") == tr.label("category", c)))

            # a result generated before a segment change is labelled; language switch does not regenerate
            if pair:
                a, b, c = pair
                choose(pg, "Segment", tr.label("segment", a))
                settle()
                choose(pg, "Garment category", tr.label("category", c))
                settle()
                pg.get_by_role("button", name="Generate recommendations").click()
                settle()
                before = pg.inner_text("body")
                choose(pg, "Segment", tr.label("segment", b))
                settle()
                body = pg.inner_text("body")
                prev = f"Segment: {tr.label('segment', a)} · Garment category: {tr.label('category', c)}"
                checks.append(("result before the segment change is labelled as the previous request",
                               "settings changed" in body and prev in body))
                pg.screenshot(path=str(out / "categories_en_stale_result.png"), full_page=True)
                pg.get_by_role("radio", name="TR", exact=True).first.click()
                settle()
                body_tr = pg.inner_text("body")
                trt = get_translator("tr")
                checks.append(("TR: same labelling, selection kept", "önceki isteğe aittir" in body_tr
                               and selected(pg, "Hedef grup") == trt.label("segment", b)))
                status = [ln for ln in before.splitlines() if "generated in" in ln]
                status_tr = [ln for ln in body_tr.splitlines() if "sn içinde üretildi" in ln]
                checks.append(("language switch did not regenerate (same generation time)", bool(status) and bool(status_tr)
                               and status[0].split(" s ")[0].split()[-1] == status_tr[0].split(" sn")[0].replace(",", ".")))
                pg.screenshot(path=str(out / "categories_tr_stale_result.png"), full_page=True)
            br.close()
    finally:
        proc.terminate()
        proc.wait(timeout=20)
        tmp.cleanup()
    checks.append(("no browser console errors", not console_errors))
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    print(json.dumps(evidence, ensure_ascii=False, indent=1))
    print(f"browser console errors: {len(console_errors)}")
    for e in console_errors[:10]:
        print("  ", e[:200])
    return 0 if checks and all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
