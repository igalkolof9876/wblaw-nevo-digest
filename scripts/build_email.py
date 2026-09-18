# -*- coding: utf-8 -*-
"""
Render the daily judgment analyses into a polished RTL HTML email.

Input JSON (written by Claude after analysing each judgment):
{
  "date": "18/08/2026",
  "sources": ["גיליון 327 (17/08/2026)", "גיליון 328 (18/08/2026)"],
  "items": [
    {"case","court","judge","date","pages","topic","url","headline",
     "sections": {"facts","arguments","discussion","nuances"}}
  ],
  "skipped": [{"case","topic","reason"}],
  "stats": {"scanned": 41, "filtered_topic": 12, "filtered_short": 3}
}

Usage: python build_email.py --in analyses.json --out digest.html
Email clients ignore external CSS and web fonts, so every rule is inline and
the font stack is system-only.
"""
import re, sys, json, html, argparse

sys.stdout.reconfigure(encoding="utf-8")

# Geometric Hebrew sans. Heebo / Open Sans are used when installed locally
# (and pulled from Google Fonts by clients that allow it); otherwise the stack
# degrades to the squarest system faces available.
FONT = ("Heebo, 'Open Sans', Assistant, Rubik, 'Noto Sans Hebrew', "
        "'Segoe UI', Arial, sans-serif")
SERIF = FONT  # body text stays in the same geometric sans, by request

INK = "#18222c"
MUTED = "#66757f"
LINE = "#e2e7eb"
ACCENT = "#15496e"
SOFT = "#f2f5f7"
GOLD = "#a07c2c"
GREEN = "#0e7a4b"

SECTIONS = [
    ("facts", "התשתית העובדתית", "1"),
    ("arguments", "הטיעונים והעילות המשפטיות", "2"),
    ("discussion", "הדיון המשפטי והמסקנות", "3"),
    ("nuances", "ניואנסים עובדתיים ומה היה עשוי לשנות את התוצאה", "4"),
]


def esc(s):
    return html.escape(s or "", quote=False)


def rich(text):
    """Blank-line separated paragraphs; **bold**; '- ' bullet lists."""
    if not text:
        return ""
    blocks = re.split(r"\n\s*\n", text.strip())
    out = []
    for b in blocks:
        lines = [l.strip() for l in b.split("\n") if l.strip()]
        if lines and all(l.startswith(("- ", "• ", "* ")) for l in lines):
            items = "".join(
                "<li style=\"margin:0 0 7px 0;\">%s</li>" % bold(esc(l[2:].strip()))
                for l in lines)
            out.append('<ul style="margin:0 0 14px 0; padding-right:20px; '
                       'padding-left:0; color:%s; font:16px/1.9 %s;">%s</ul>'
                       % (INK, SERIF, items))
        else:
            out.append('<p style="margin:0 0 14px 0; color:%s; font:16px/1.9 %s; '
                       'text-align:justify;">%s</p>'
                       % (INK, SERIF, bold(esc(" ".join(lines)))))
    return "".join(out)


def bold(s):
    return re.sub(r"\*\*(.+?)\*\*",
                  r'<strong style="color:%s;">\1</strong>' % ACCENT, s)


def meta_chip(label, value):
    if not value:
        return ""
    return ('<td style="padding:0 0 0 18px; vertical-align:top; white-space:nowrap;">'
            '<div style="font:11px/1.4 %s; color:%s; letter-spacing:.4px;">%s</div>'
            '<div style="font:14px/1.5 %s; color:%s; font-weight:600;">%s</div></td>'
            % (FONT, MUTED, esc(label), FONT, INK, esc(str(value))))


def card(it, n):
    s = it.get("sections", {})
    body = ""
    for key, title, num in SECTIONS:
        if not s.get(key):
            continue
        body += (
            '<tr><td style="padding:22px 26px 0 26px;">'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
            'width="100%%"><tr>'
            '<td style="width:26px; vertical-align:top; padding-top:2px;">'
            '<div style="width:23px; height:23px; border-radius:3px; background:%s; '
            'color:#fff; font:12px/23px %s; text-align:center; font-weight:700;">%s</div>'
            '</td>'
            '<td style="padding-right:10px;">'
            '<div style="font:15px/1.5 %s; font-weight:700; color:%s; '
            'letter-spacing:.2px; margin-bottom:9px;">%s</div>%s</td>'
            '</tr></table></td></tr>'
            % (ACCENT, FONT, num, FONT, ACCENT, esc(title), rich(s.get(key))))

    head_meta = "".join([
        meta_chip("ערכאה", it.get("court")),
        meta_chip("מותב", it.get("judge")),
        meta_chip("תאריך", it.get("date")),
        meta_chip("היקף", ("%s ע'" % it["pages"]) if it.get("pages") else None),
    ])

    link = ""
    if it.get("url"):
        link = ('<tr><td style="padding:18px 26px 26px 26px;">'
                '<a href="%s" style="display:inline-block; font:13px/1 %s; '
                'font-weight:600; color:#fff; background:%s; text-decoration:none; '
                'padding:11px 22px; border-radius:3px;">קריאת פסק הדין המלא באתר נבו '
                '&#8592;</a></td></tr>' % (esc(it["url"]), FONT, ACCENT))

    headline = ""
    if it.get("headline"):
        headline = ('<tr><td style="padding:16px 26px 4px 26px;">'
                    '<div style="border-right:3px solid %s; background:%s; '
                    'padding:13px 16px;">'
                    '<div style="font:15px/1.5 %s; font-weight:700; color:%s; '
                    'letter-spacing:.2px; margin-bottom:8px;">השורה התחתונה</div>'
                    '<div style="font:15px/1.75 %s; color:%s; '
                    'font-weight:500;">%s</div></div></td></tr>'
                    % (GOLD, "#fbf7ef", FONT, GREEN, SERIF, "#4a3d20", esc(it["headline"])))

    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'width="100%%" style="background:#ffffff; border:1px solid %s; '
        'border-radius:3px; margin:0 0 26px 0;">'
        '<tr><td style="padding:24px 26px 0 26px; border-top:3px solid %s; '
        'border-radius:3px 3px 0 0;">'
        '<div style="font:12px/1.4 %s; color:%s; letter-spacing:1.5px; '
        'text-transform:uppercase; margin-bottom:6px; font-weight:600;">%s</div>'
        '<div style="font:17px/1.4 %s; font-weight:700; color:%s; '
        'margin-bottom:10px;">%s</div>'
        '<div style="font:20px/1.5 %s; font-weight:700; color:%s;">%s</div>'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin-top:16px; padding-top:14px; border-top:1px solid %s; '
        'width:100%%;"><tr>%s</tr></table>'
        '</td></tr>%s%s%s</table>'
        % (LINE, ACCENT, FONT, MUTED, esc("פסק דין %d" % n),
           FONT, GOLD, esc(it.get("topic") or ""),
           SERIF, INK, esc(it.get("case", "")),
           LINE, head_meta, headline, body, link))


def build(d):
    items = d.get("items", [])
    toc = ""
    if len(items) > 1:
        rows = "".join(
            '<tr><td style="padding:7px 0; border-bottom:1px solid %s;">'
            '<span style="display:inline-block; width:20px; font:12px/1.6 %s; '
            'color:%s; font-weight:700;">%d</span>'
            '<span style="font:14px/1.6 %s; color:%s;">%s</span>'
            '<span style="font:12px/1.6 %s; color:%s;"> &nbsp;·&nbsp; %s</span>'
            '</td></tr>'
            % (LINE, FONT, ACCENT, i, SERIF, INK, esc(it.get("case", "")),
               FONT, MUTED, esc(it.get("topic") or ""))
            for i, it in enumerate(items, 1))
        toc = ('<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
               'width="100%%" style="background:#fff; border:1px solid %s; '
               'border-radius:3px; margin:0 0 26px 0;"><tr><td style="padding:20px 26px;">'
               '<div style="font:12px/1.4 %s; color:%s; letter-spacing:1px; '
               'margin-bottom:10px;">בגיליון זה</div>'
               '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
               'width="100%%">%s</table></td></tr></table>' % (LINE, FONT, MUTED, rows))

    if items:
        cards = "".join(card(it, i) for i, it in enumerate(items, 1))
    else:
        cards = ('<table role="presentation" width="100%%" style="background:#fff; '
                 'border:1px solid %s; border-radius:3px;"><tr>'
                 '<td style="padding:34px 26px; text-align:center; font:16px/1.7 %s; '
                 'color:%s;">לא נמצאו פסקי דין בתחומי העניין שהוגדרו '
                 'בסריקה של היום.</td></tr></table>' % (LINE, SERIF, MUTED))

    st = d.get("stats", {})
    bits = []
    if st.get("scanned"):
        bits.append("נסרקו %d פסקי דין" % st["scanned"])
    if st.get("filtered_topic"):
        bits.append("%d סוננו לפי נושא" % st["filtered_topic"])
    if st.get("filtered_short"):
        bits.append("%d סוננו בשל היקף" % st["filtered_short"])
    bits.append("%d נותחו" % len(items))
    stats_line = " &nbsp;·&nbsp; ".join(esc(b) for b in bits)

    skipped = ""
    if d.get("skipped"):
        rows = "".join(
            '<div style="font:13px/1.8 %s; color:%s;">· %s <span style="color:%s;">'
            '(%s)</span></div>' % (FONT, MUTED, esc(x.get("case", "")), "#93a1ad",
                                   esc(x.get("reason", "")))
            for x in d["skipped"])
        skipped = ('<table role="presentation" width="100%%" cellpadding="0" '
                   'cellspacing="0" border="0" style="margin-top:6px;"><tr>'
                   '<td style="padding:18px 26px; background:#eef2f5; '
                   'border-radius:3px;">'
                   '<div style="font:12px/1.4 %s; color:%s; letter-spacing:1px; '
                   'margin-bottom:8px;">נסרקו ולא נותחו</div>%s</td></tr></table>'
                   % (FONT, MUTED, rows))

    sources = ""
    if d.get("sources"):
        sources = ('<div style="font:12px/1.7 %s; color:%s; margin-top:6px;">מקור: %s</div>'
                   % (FONT, "#94a6b3", esc(" · ".join(d["sources"]))))

    return """<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700&family=Open+Sans:wght@400;600;700&display=swap');
</style>
<div dir="rtl" lang="he" style="margin:0; padding:0; background:%s;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%%" style="background:%s; padding:26px 12px;">
<tr><td align="center">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="680" style="width:680px; max-width:100%%;">
  <tr><td style="padding:0 0 22px 0;">
    <div style="border-bottom:2px solid %s; padding-bottom:16px;">
      <div style="font:12px/1.4 %s; color:%s; letter-spacing:2px;">מעקב פסיקה יומי</div>
      <div style="font:31px/1.35 %s; font-weight:700; color:%s; margin-top:5px;">סקירת פסיקה &#8211; %s</div>
      <div style="font:16px/1.7 %s; color:%s; margin-top:7px;">%s</div>
      %s
    </div>
  </td></tr>
  <tr><td>%s%s%s</td></tr>
  <tr><td style="padding:22px 4px 0 4px;">
    <div style="font:11px/1.7 %s; color:#9aabb7; border-top:1px solid %s; padding-top:14px;">
      הופק אוטומטית מגיליון פד&quot;י-מייל (פסיקה) של נבו. הסקירה היא תמצית עבודה ואינה תחליף לקריאת פסק הדין במלואו או לייעוץ משפטי.
    </div>
  </td></tr>
</table>
</td></tr></table></div>""" % (
        SOFT, SOFT, ACCENT, FONT, GOLD, SERIF, INK, esc(d.get("date", "")),
        FONT, MUTED, stats_line, sources, toc, cards, skipped, FONT, LINE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = json.load(open(a.inp, encoding="utf-8"))
    open(a.out, "w", encoding="utf-8").write(build(d))
    print("wrote %s (%d items)" % (a.out, len(d.get("items", []))))


if __name__ == "__main__":
    main()
