# -*- coding: utf-8 -*-
"""
Prepare digest.html for PDF printing.

Why this exists (2026-09-16): digest.html is an EMAIL layout - a fixed 680px
table inside a wrapper with 12px side padding. Printed to A4 with default
margins the content is wider than the printable area, so the overflowing edge
is clipped. In an RTL document the clipped edge is the LEFT one, which is what
Igal saw: "the PDF arrives with its left margin cut off".

This script produces a print-specific copy:
  - drops the Google Fonts @import (external fetch during print, and it roughly
    triples the PDF size by embedding the webfont - the font stack already has
    Segoe UI / Noto Sans Hebrew fallbacks that render Hebrew correctly)
  - adds @page margins and forces the fixed-width table to fit the page
  - keeps cards from being split across pages where possible

digest.html itself is left untouched, because the email and the Artifact both
need the original fixed-width layout.
"""
import argparse, io, re

PRINT_CSS = """<style>
@page { size: A4 portrait; margin: 11mm 10mm 13mm 10mm; }
html, body {
  margin: 0 !important; padding: 0 !important;
  background: #ffffff !important;
  -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important;
}
/* the outer grey gutter pushes the content past the printable area */
body > div > table, div[dir="rtl"] > table { padding: 0 !important; background: #ffffff !important; }
/* An email table uses auto layout, so a line that cannot wrap makes the whole
   table wider than the page and the overflow is clipped - on the LEFT in RTL.
   The index rows at the top join the case name and the topic with &nbsp;, which
   is exactly such a line. Fixed layout plus forced wrapping keeps everything
   inside the page box. */
table { table-layout: fixed !important; width: 100% !important; max-width: 100% !important; }
table[width="680"] { width: 100% !important; max-width: 100% !important; }
td, th, div, span, a, p, li { white-space: normal !important; overflow-wrap: anywhere !important; }
img { max-width: 100% !important; }
/* keep a judgment card intact on one page where it fits */
/* Flatten the outer email scaffolding for print. The cards are sibling tables
   inside one table cell, and Chromium handles a forced page break inside a
   table cell badly: it emitted stray near-empty pages. Turning only the two
   outer wrapper tables into normal block flow makes the breaks land cleanly.
   The card tables themselves stay tables, because the meta row needs columns. */
div[dir="rtl"] > table, div[dir="rtl"] > table > tbody,
div[dir="rtl"] > table > tbody > tr, div[dir="rtl"] > table > tbody > tr > td,
table[width="680"], table[width="680"] > tbody,
table[width="680"] > tbody > tr, table[width="680"] > tbody > tr > td {
  display: block !important; width: auto !important; max-width: 100% !important;
}

/* The last row of a card is the "read the full judgment" button. When a card
   ended just past a page boundary that button spilled onto a page of its own,
   which is what the near-empty pages were. Ask for no break right before it. */
.nv-cta { page-break-before: avoid !important; break-before: avoid !important; }
/* no trailing gutter needed, every card already starts its own page */
.nv-card { margin-bottom: 0 !important; }

/* Each judgment starts on a fresh page. */
.nv-card { page-break-before: always; break-before: page; }
/* Do NOT set page-break-inside:avoid on rows or cells. A judgment card is
   taller than a page, so "avoid" pushes the whole card to the next page and
   leaves most of the previous one blank. That is where the white gaps came
   from (Igal, 16.9.2026). Cards must be free to flow across pages. */
tr, td, table { page-break-inside: auto; break-inside: auto; }
div, p { orphans: 2; widows: 2; }
</style>"""

# The opening tag of a judgment card as emitted by build_email.py, once per judgment.
# Tagging it with a class is what lets the stylesheet above break pages per judgment.
CARD_OPEN = ('<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
             'style="background:#ffffff; border:1px solid #e2e7eb; border-radius:3px; margin:0 0 26px 0;">')
CARD_OPEN_TAGGED = CARD_OPEN.replace('<table role="presentation"', '<table class="nv-card" role="presentation"')

# the final row of each card, holding the "read on Nevo" button
CTA_OPEN = '<tr><td style="padding:18px 26px 26px 26px;"><a href="https://www.nevo.co.il'
CTA_OPEN_TAGGED = CTA_OPEN.replace('<tr>', '<tr class="nv-cta">')



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    args = ap.parse_args()

    html = io.open(args.src, encoding="utf-8").read()

    # drop the webfont import block (external CSP-blocked fetch + PDF bloat)
    html = re.sub(r"<style>\s*@import url\([^)]*\);\s*</style>", "", html, count=1)
    html = re.sub(r"@import url\([^)]*\);", "", html)

    cards = html.count(CARD_OPEN)
    html = html.replace(CARD_OPEN, CARD_OPEN_TAGGED)
    ctas = html.count(CTA_OPEN)
    html = html.replace(CTA_OPEN, CTA_OPEN_TAGGED)
    print("tagged %d judgment cards and %d buttons" % (cards, ctas))

    out = PRINT_CSS + "\n" + html
    io.open(args.dst, "w", encoding="utf-8").write(out)
    print("wrote %s (%d chars)" % (args.dst, len(out)))


if __name__ == "__main__":
    main()
