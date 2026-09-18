# -*- coding: utf-8 -*-
"""
Turn a digest.html (built for email — table-based, fixed widths, no viewport
meta, because it must survive Outlook/Exchange stripping) into a page fit to
publish as a Claude Artifact (a real browser, so CSS/media-queries work, but
it still needs to actually be responsive on a phone — a browser rendering a
fixed 680px table with a missing viewport tag looks "zoomed out" on mobile,
confirmed by Igal 2026-08-22).

Two independent fixes, neither touching the email-safe generator itself:
1. Strip the Google-Fonts @import (Artifact CSP blocks external font loads).
2. Add a <meta viewport> tag and a mobile <style> block with !important
   overrides — inline styles otherwise always beat a stylesheet, so the
   680px/560px table widths and the nowrap meta-chip cells need !important
   to actually shrink/wrap under ~700px.

Usage: python prep_artifact.py --in digest.html --out digest_artifact.html --title "..."
"""
import re, sys, argparse

sys.stdout.reconfigure(encoding="utf-8")

MOBILE_CSS = """<style>
@media (max-width: 700px) {
  table[width="680"] { width: 100% !important; }
  td[style*="white-space:nowrap"] { white-space: normal !important; padding-bottom: 10px !important; }
}
</style>
<meta name="viewport" content="width=device-width, initial-scale=1">
"""


def prep(html, title):
    html = re.sub(r"<style>\s*@import[^<]*</style>\s*", "", html, count=1)
    return "<title>%s</title>\n%s%s" % (title, MOBILE_CSS, html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", required=True)
    a = ap.parse_args()
    html = open(a.inp, encoding="utf-8").read()
    out = prep(html, a.title)
    open(a.out, "w", encoding="utf-8").write(out)
    print("wrote %s (%d chars)" % (a.out, len(out)))


if __name__ == "__main__":
    main()
