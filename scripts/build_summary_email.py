# -*- coding: utf-8 -*-
"""
Render a short, fully inline-styled (Outlook/Exchange-safe) doorway email that
links to the full digest published as a Claude Artifact.

Why this exists: the full digest (18 in-depth, 600-1000+ word analyses) is too
large and too CSS-dependent (needs a <style> block + flexbox) to render
reliably inside an email client. Corporate mail systems (Outlook/Exchange, and
most security gateways such as Mimecast/Proofpoint/Microsoft ATP) strip
<style> blocks and ignore flexbox, showing an unstyled wall of text. Every
rule here is therefore INLINE and layout is table-based, which survives that
scrubbing.

This email is deliberately minimal - a doorway, not a second digest. Per-item
teasers were tried and rejected (2026-08-22): three compressed lines per
judgment gave no real value and duplicated, at low fidelity, content that
already exists in full behind the link. The email states what's inside in
one line and gets out of the way; the Artifact itself has the full
per-judgment table of contents.

Usage:
  python build_summary_email.py --in analyses.json --url <artifact_url> --out summary_email.html
"""
import re
import sys, json, html, argparse

sys.stdout.reconfigure(encoding="utf-8")

FONT = "Heebo,Arial,sans-serif"
INK = "#18222c"
MUTED = "#66757f"
LINE = "#e2e7eb"
ACCENT = "#15496e"
SOFT = "#f2f5f7"
GOLD = "#a07c2c"


def esc(s):
    return html.escape(s or "", quote=False)


def cta(url, has_pdf=False):
    """A button when the full digest is published somewhere; otherwise a line
    telling the reader the full report is attached to this message.

    The button's color MUST live on the <td> (via the legacy `bgcolor`
    attribute AND an inline style, not on the <a> itself): Outlook Web Access
    strips the `background`/`background-color` declaration specifically off
    <a> tags while leaving `color` untouched, which silently produced white
    text on a white card (invisible button, confirmed by Igal 2026-08-22 with
    a screenshot - the link text was present in the source but not visible).
    A plain-text fallback URL is also printed below the button so the digest
    is always reachable even if a client mangles the button further.

    has_pdf: the Claude mobile app doesn't recognize claude.ai/code/artifact
    URLs (a Claude Code-specific route) and shows its own 404 (confirmed by
    Igal 2026-08-22 on his phone) even though the page is real. The PDF
    attachment is an ADDITION, not a replacement, for exactly that case -
    say so explicitly so the primary link stays primary.
    """
    if url:
        button = (
            '<tr><td style="padding:0 30px 6px 30px;">'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%%">'
            '<tr><td bgcolor="%s" style="background-color:%s;text-align:center;padding:18px 20px;">'
            '<a href="%s" style="font:700 16px/1 %s;color:#ffffff;text-decoration:none;">'
            'לצפייה בסקירה המלאה &#8592;</a>'
            '</td></tr></table></td></tr>'
            % (ACCENT, ACCENT, esc(url), FONT))
        fallback = (
            '<tr><td style="padding:0 30px 8px 30px;text-align:center;">'
            '<a href="%s" style="font:12px/1.6 %s;color:%s;">%s</a></td></tr>'
            % (esc(url), FONT, MUTED, esc(url)))
        pdf_note = ""
        if has_pdf:
            pdf_note = (
                '<tr><td style="padding:0 30px 8px 30px;text-align:center;">'
                '<div style="font:12px/1.6 %s;color:%s;">📱 לצפייה ממכשיר נייד: '
                'הסקירה המלאה מצורפת גם כקובץ PDF להודעה זו</div></td></tr>'
                % (FONT, MUTED))
        return button + fallback + pdf_note
    return ('<tr><td style="padding:0 30px 8px 30px;">'
            '<div style="font:13px/1.7 %s;color:%s;background:%s;padding:12px 14px;'
            'border-right:3px solid %s;">הסקירה המלאה מצורפת להודעה זו כקובץ '
            '<strong>digest.html</strong> &#8212; לפתיחה בדפדפן.</div></td></tr>'
            % (FONT, INK, SOFT, GOLD))


def build(d, url, has_pdf=False):
    items = d.get("items", [])
    st = d.get("stats", {})
    bits = []
    if st.get("scanned"):
        bits.append("נסרקו %d פסקי דין" % st["scanned"])
    if st.get("filtered_topic"):
        bits.append("%d סוננו לפי נושא" % st["filtered_topic"])
    bits.append("%d נותחו לעומק" % len(items))
    stats_line = " &nbsp;·&nbsp; ".join(esc(b) for b in bits)

    if items:
        topics = []
        for it in items:
            # 2026-09-16: was split(" – ") only. Nevo topic paths use an EN dash, so any
            # normalisation to a plain hyphen made the split silently fail and the full
            # topic path leaked into the domain list, with duplicates. Prefer the clean
            # category field, and fall back to a dash-agnostic split.
            t = (it.get("category") or "").strip()
            if not t:
                t = re.split(r"\s[–--]\s", it.get("topic") or "")[0].strip()
            if t and t not in topics:
                topics.append(t)
        scope_line = ("הניתוח המלא - עובדות, טענות, דיון משפטי וניואנסים לכל פסק דין - "
                      "נמצא בקישור. תחומים בגיליון היום: %s." % esc(", ".join(topics)))
    else:
        scope_line = "לא נמצאו פסקי דין בתחומי העניין שהוגדרו בסריקה של היום."

    return """<div dir="rtl" lang="he" style="margin:0;padding:0;background:%s;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%%" style="background:%s;padding:28px 12px;">
<tr><td align="center">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="560" style="width:560px;max-width:100%%;background:#ffffff;border:1px solid %s;">
  <tr><td style="padding:34px 34px 24px 34px;border-top:4px solid %s;">
    <div style="font:12px/1.4 %s;color:%s;letter-spacing:2px;">מעקב פסיקה יומי</div>
    <div style="font:26px/1.35 %s;font-weight:700;color:%s;margin-top:6px;">סקירת פסיקה &#8211; %s</div>
    <div style="font:13px/1.7 %s;color:%s;margin-top:8px;">%s</div>
  </td></tr>
  %s
  <tr><td style="padding:14px 34px 0 34px;">
    <div style="font:14px/1.8 %s;color:%s;">%s</div>
  </td></tr>
  <tr><td style="padding:26px 34px 30px 34px;">
    <div style="font:11px/1.7 %s;color:#9aabb7;border-top:1px solid %s;padding-top:14px;">
      הופק אוטומטית מגיליון פד&quot;י-מייל (פסיקה) של נבו. הסקירה היא תמצית עבודה ואינה תחליף לקריאת פסק הדין במלואו או לייעוץ משפטי.
    </div>
  </td></tr>
</table>
</td></tr></table></div>""" % (
        SOFT, SOFT, LINE, ACCENT, FONT, MUTED, FONT, INK, esc(d.get("date", "")),
        FONT, MUTED, stats_line, cta(url, has_pdf), FONT, INK, scope_line, FONT, LINE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--url", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--has-pdf", action="store_true",
                     help="mention the PDF-attachment mobile fallback")
    a = ap.parse_args()
    d = json.load(open(a.inp, encoding="utf-8"))
    out = build(d, a.url, a.has_pdf)
    open(a.out, "w", encoding="utf-8").write(out)
    print("wrote %s (%d chars, %d items)" % (a.out, len(out), len(d.get("items", []))))


if __name__ == "__main__":
    main()
