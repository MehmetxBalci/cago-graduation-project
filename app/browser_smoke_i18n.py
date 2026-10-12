"""Real-browser smoke test of the bilingual UI (V1.1.0; Playwright + Chromium, not part of requirements.txt).

    pip install playwright && python -m playwright install chromium          # once
    python -m app.browser_smoke_i18n [--out docs/demo_screenshots] [--fixture-data]

Starts `streamlit run app/streamlit_app.py` headless on a free port and checks, in a real browser:
  1. English is the default language        2. switching to TR translates the form and the results
  3. the Turkish form is usable              4. switching back to EN restores the English UI
  5. selections and the generated result are preserved (same status line incl. generation time, same result digest)
  6. no regeneration happens on a language switch (no progress bar, identical timing / digest)
  7. no browser console errors
and saves screenshots of both language modes for the SAME generated recommendation.

Data: the app's normal processed folder (or `CAGO_PROCESSED_DIR`). `--fixture-data` instead writes the SYNTHETIC test fixture
(app/tests/app_fixtures.py) to a temporary folder -- use it only where the real processed data is unavailable; screenshots
then show synthetic garments. Exit code 0 = all checks passed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.browser_smoke import free_port, wait_http  # noqa: E402

CHROMIUM_FALLBACK = "/opt/pw-browsers/chromium"


def write_fixture_data(d: Path) -> Path:
    from app.tests.app_fixtures import CAPS, REP_ALL, VOCAB_DOC
    REP_ALL.to_parquet(d / "garment_representation.parquet")
    (d / "ml_material_vocabulary.json").write_text(json.dumps(VOCAB_DOC), encoding="utf-8")
    (d / "category_capabilities.json").write_text(json.dumps(CAPS), encoding="utf-8")
    return d


def choose(pg, label: str, option_text: str) -> None:
    box = pg.locator(f'input[aria-label="{label}"]').first
    box.click()
    pg.get_by_role("option", name=option_text, exact=True).first.click()
    pg.wait_for_timeout(700)


def selected(pg, label: str) -> str:
    """Displayed value of a selectbox (Streamlit renders it next to the input with the given aria-label)."""
    return pg.locator(f'input[aria-label="{label}"]').first.input_value().strip()


def launch(p):
    try:
        return p.chromium.launch()
    except Exception:                                    # bundled browser of another Playwright version
        return p.chromium.launch(executable_path=os.environ.get("CAGO_CHROMIUM", CHROMIUM_FALLBACK))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "demo_screenshots"))
    ap.add_argument("--fixture-data", action="store_true", help="use the SYNTHETIC test fixture instead of the processed data")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    tmp = tempfile.TemporaryDirectory()
    env = {**os.environ, "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false"}
    if args.fixture_data:
        env["CAGO_PROCESSED_DIR"] = str(write_fixture_data(Path(tmp.name)))
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"), "--server.headless", "true",
                             "--server.port", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    checks: list[tuple[str, bool]] = []
    console_errors: list[str] = []
    evidence: dict = {"data": "SYNTHETIC test fixture" if args.fixture_data else "processed data folder"}
    try:
        url = f"http://localhost:{port}"
        wait_http(url + "/_stcore/health")
        with sync_playwright() as p:
            br = launch(p)
            pg = br.new_page(viewport={"width": 1500, "height": 2300})
            pg.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))

            def settle():
                pg.wait_for_timeout(800)
                pg.wait_for_function("() => !document.body.innerText.includes('Running...')", timeout=120_000)
                pg.wait_for_timeout(1200)

            def switch(code: str):
                pg.get_by_role("radio", name=code, exact=True).first.click()
                settle()

            def status_line(body: str) -> str:
                m = re.search(r"^.*(generated in|sn içinde üretildi).*$", body, re.M)
                return m.group(0) if m else ""

            def digest() -> str:
                for name in ("Technical details", "Teknik ayrıntılar"):
                    for el in pg.get_by_text(name, exact=True).all():
                        el.click()
                        pg.wait_for_timeout(300)
                m = re.search(r'"digest":\s*"([0-9a-f]+)"', pg.inner_text("body"))
                return m.group(1) if m else ""

            # 1. English default
            pg.goto(url)
            pg.get_by_text("Generate recommendations").first.wait_for(timeout=120_000)
            body = pg.inner_text("body")
            checks.append(("1 EN is the default language", "Generate recommendations" in body and "Your garment" in body
                           and "does not guarantee recyclability" in body))
            pg.get_by_role("radio", name="TR", exact=True).first.wait_for(timeout=30_000)
            checks.append(("1 TR / EN switcher visible", pg.get_by_role("radio", name="TR", exact=True).first.is_visible()
                           and pg.get_by_role("radio", name="EN", exact=True).first.is_visible()))

            # generate once in English
            choose(pg, "Preferred dominant material", "linen")
            choose(pg, "Fit", "relaxed")
            choose(pg, "Breathability", "high")
            pg.get_by_role("button", name="Generate recommendations").click()
            settle()
            pg.get_by_text("Pareto candidate overview").wait_for(timeout=120_000)
            body = pg.inner_text("body")
            en_status, en_digest = status_line(body), digest()
            evidence.update(en_status=en_status, en_digest=en_digest)
            checks.append(("EN results rendered", "Balanced" in body and "Sorting-focused" in body and bool(en_digest)))
            for name in ("Why this recommendation", "SR1–SR5 sorting-screening results"):
                for el in pg.get_by_text(name, exact=True).all():
                    el.click()
                    pg.wait_for_timeout(200)
            pg.screenshot(path=str(out / "i18n_01_en_results.png"), full_page=True)

            # 2./3. switch to Turkish
            switch("TR")
            pg.get_by_text("Pareto adaylarına genel bakış").wait_for(timeout=60_000)
            body = pg.inner_text("body")
            tr_status, tr_digest = status_line(body), digest()
            evidence.update(tr_status=tr_status, tr_digest=tr_digest)
            checks.append(("2 TR form translated", all(s in body for s in ("Giysiniz", "Önerileri üret", "Tercih edilen baskın malzeme",
                                                                         "Fonksiyonel tercihler"))))
            checks.append(("3 TR results translated", all(s in body for s in ("Dengeli", "Ayıklama Odaklı", "Tercihlere Uyum",
                                                                            "Prototip uyarısı"))))
            checks.append(("5 selections preserved in TR", (selected(pg, "Tercih edilen baskın malzeme"), selected(pg, "Kesim"),
                                                            selected(pg, "Nefes alabilirlik")) == ("Keten", "Rahat kesim", "Yüksek")))
            checks.append(("6 no regeneration on EN->TR (same digest, same timing)", tr_digest == en_digest and bool(tr_digest)
                           and re.findall(r"[\d.,]+", en_status)[:1] == [x.replace(",", ".") for x in re.findall(r"[\d.,]+", tr_status)][:1]))
            checks.append(("TR: results not marked stale", "ayarlar değişti" not in body))
            for name in ("Bu öneri neden seçildi", "SR1–SR5 ayıklama tarama sonuçları"):
                for el in pg.get_by_text(name, exact=True).all():
                    el.click()
                    pg.wait_for_timeout(200)
            pg.screenshot(path=str(out / "i18n_02_tr_results.png"), full_page=True)

            # Turkish form usable: change a value with Turkish labels (marks results stale, does not regenerate)
            choose(pg, "Esneme", "Düşük")
            body = pg.inner_text("body")
            checks.append(("3 TR form usable (stale warning in Turkish, no automatic regeneration)",
                           "ayarlar değişti" in body and digest() == en_digest))
            choose(pg, "Esneme", "Tercih yok")

            # 4./5. back to English
            switch("EN")
            pg.get_by_text("Pareto candidate overview").wait_for(timeout=60_000)
            body = pg.inner_text("body")
            back_status, back_digest = status_line(body), digest()
            evidence.update(back_status=back_status, back_digest=back_digest)
            checks.append(("4 EN restored", "Generate recommendations" in body and "Balanced" in body and "Dengeli" not in body))
            checks.append(("5 selections preserved after TR->EN", (selected(pg, "Preferred dominant material"), selected(pg, "Fit"),
                                                                  selected(pg, "Breathability"), selected(pg, "Stretch"))
                           == ("linen", "relaxed", "high", "No preference")))
            checks.append(("6 no regeneration on TR->EN (identical status line and digest)", back_status == en_status and back_digest == en_digest))
            checks.append(("EN: results not marked stale", "settings changed" not in body))
            pg.screenshot(path=str(out / "i18n_03_en_after_switch.png"), full_page=True)
            br.close()
    finally:
        proc.terminate()
        proc.wait(timeout=20)
        tmp.cleanup()
    checks.append(("7 no browser console errors", not console_errors))
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    print(json.dumps(evidence, ensure_ascii=False, indent=1))
    print(f"browser console errors: {len(console_errors)}")
    for e in console_errors[:10]:
        print("  ", e[:200])
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
