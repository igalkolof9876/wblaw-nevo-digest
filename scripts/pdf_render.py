# -*- coding: utf-8 -*-
"""
Render digest_print.html to PDF in the cloud sandbox (no Windows/Edge available).

Cloud replacement for the old local step:
  & msedge.exe --headless=new --print-to-pdf=...

Uses Playwright + headless Chromium, the same engine already confirmed present
in this account's cloud routine environment (seen at /opt/pw-browsers/chromium
in a prior routine run). Falls back to a plain `playwright install chromium`
if that fixed path is not there, since the exact path may differ per environment.
"""
import argparse, os, subprocess, sys

KNOWN_CHROMIUM_PATHS = [
    "/opt/pw-browsers/chromium",
    "/opt/pw-browsers/chromium/chrome-linux/chrome",
]


def ensure_playwright():
    try:
        import playwright  # noqa
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "playwright"])


def find_chromium():
    for p in KNOWN_CHROMIUM_PATHS:
        if os.path.exists(p):
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    args = ap.parse_args()

    ensure_playwright()
    from playwright.sync_api import sync_playwright

    src_path = os.path.abspath(args.src)
    executable_path = find_chromium()

    with sync_playwright() as p:
        launch_kwargs = {}
        if executable_path:
            launch_kwargs["executable_path"] = executable_path
        try:
            browser = p.chromium.launch(**launch_kwargs)
        except Exception:
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("file://" + src_path)
        page.pdf(path=args.dst, format="A4", print_background=True)
        browser.close()

    print("wrote %s" % args.dst)


if __name__ == "__main__":
    main()
