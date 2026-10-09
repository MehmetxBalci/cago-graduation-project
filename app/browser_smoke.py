"""Optional real-browser smoke test of the Streamlit app (Playwright + Chromium; not part of requirements.txt).

    pip install playwright && python -m playwright install chromium     # once
    python -m app.browser_smoke [--out docs/demo_screenshots]

Starts `streamlit run app/streamlit_app.py` headless on a free port, drives scenarios S1, S2, S3 and S5 of
docs/V1_DEMO_SCENARIOS.md through the sidebar form, checks the rendered text and saves screenshots. Exit code 0 = all checks passed.
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_http(url: str, timeout: float = 60) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"server did not start: {url}")


def choose(pg, label: str, value: str) -> None:
    box = pg.locator(f'input[aria-label="{label}"]').first
    box.click()
    box.fill(value)
    box.press("Enter")
    pg.wait_for_timeout(600)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "demo_screenshots"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    port = free_port()
    env = {**os.environ, "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false"}
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"), "--server.headless", "true",
                             "--server.port", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    checks: list[tuple[str, bool]] = []
    console_errors: list[str] = []
    try:
        url = f"http://localhost:{port}"
        wait_http(url + "/_stcore/health")
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page(viewport={"width": 1500, "height": 2300})
            pg.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

            def fresh():
                pg.goto(url)
                pg.get_by_text("Generate recommendations").first.wait_for(timeout=120_000)

            def generate():
                pg.get_by_role("button", name="Generate recommendations").click()
                pg.wait_for_timeout(1000)
                pg.wait_for_function("() => !document.body.innerText.includes('Running...')", timeout=120_000)
                pg.wait_for_timeout(1500)

            # start screen
            fresh()
            body = pg.inner_text("body")
            checks.append(("start: title and disclaimer", "CAGO" in body and "does not guarantee recyclability" in body))
            pg.screenshot(path=str(out / "01_start.png"), full_page=True)

            # S2: women / trousers, linen, relaxed, breathability high
            choose(pg, "Preferred dominant material", "linen")
            choose(pg, "Fit", "relaxed")
            choose(pg, "Breathability", "high")
            generate()
            pg.get_by_text("Pareto candidate overview").wait_for(timeout=120_000)
            body = pg.inner_text("body")
            checks.append(("S2: Balanced + Intent-focused and separate Sorting-focused card",
                           "Balanced + Intent-focused" in body and "Sorting-focused" in body))
            checks.append(("S2: no exception rendered", "Traceback" not in body))
            pg.screenshot(path=str(out / "02_results.png"), full_page=True)
            for name in ("Why this recommendation", "Changes from the TRAIN template"):
                for el in pg.get_by_text(name).all():
                    el.click()
                    pg.wait_for_timeout(200)
            body = pg.inner_text("body")
            checks.append(("S2: readable preference + change wording", "Composition-based estimate" in body and "Change 1:" in body))
            pg.screenshot(path=str(out / "02b_explanations.png"), full_page=True)

            # S1: men / tshirt_polo, cotton, breathability high
            fresh()
            choose(pg, "Segment", "men")
            choose(pg, "Garment category", "tshirt polo")
            choose(pg, "Preferred dominant material", "cotton")
            choose(pg, "Breathability", "high")
            generate()
            pg.get_by_text("Pareto candidate overview").wait_for(timeout=120_000)
            body = pg.inner_text("body")
            checks.append(("S1: single card with all three roles + zero-violation wording",
                           "Balanced + Sorting-focused + Intent-focused" in body
                           and "No violations detected under the CAGO SR1–SR5 sorting-screening rules." in body))
            pg.screenshot(path=str(out / "04_single_candidate.png"), full_page=True)

            # S3: baby / skirts
            fresh()
            choose(pg, "Segment", "baby")
            choose(pg, "Garment category", "skirts")
            generate()
            body = pg.inner_text("body")
            checks.append(("S3: empty TRAIN pool explained", "no TRAIN garments for this segment and category" in body))
            pg.screenshot(path=str(out / "03_no_templates.png"), full_page=True)

            # S5: preferred linen is also forbidden; stretch high with elastane forbidden
            fresh()
            choose(pg, "Preferred dominant material", "linen")
            for m in ("linen", "elastane"):
                choose(pg, "Forbidden materials", m)
            choose(pg, "Stretch", "high")
            generate()
            body = pg.inner_text("body")
            checks.append(("S5: conflict warnings shown", "Your preferred material is also forbidden" in body
                           and "elastane is forbidden" in body))
            pg.screenshot(path=str(out / "05_conflicts.png"), full_page=True)
            br.close()
    finally:
        proc.terminate()
        proc.wait(timeout=20)
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    print(f"browser console errors: {len(console_errors)}")
    for e in console_errors[:10]:
        print("  ", e[:200])
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")       # Windows consoles / redirected output
    raise SystemExit(main())
