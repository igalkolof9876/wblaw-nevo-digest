# -*- coding: utf-8 -*-
"""
Download the full text of Nevo judgments so they can be analysed.

Usage:
    python nevo_fetch_text.py --json entries.json --outdir texts/
    python nevo_fetch_text.py --url https://www.nevo.co.il/psika_html/...htm

Writes one .txt per judgment plus an index.json mapping vid -> file, and
prints a short report. Judgment pages are public; a browser UA is required.
"""
import re, os, sys, json, html, time, argparse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA,
           "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
           "Accept-Language": "he-IL,he;q=0.9,en;q=0.8"}

BLOCK = r"(?:td|tr|div|p|br|table|li|h[1-6])"


def fetch(url, retries=3, timeout=90):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            for enc in ("utf-8", "cp1255"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace")
        except Exception as e:                       # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError("fetch failed %s: %s" % (url, last))


def to_text(doc):
    doc = re.sub(r"(?is)<(script|style|head).*?</\1>", " ", doc)
    doc = re.sub(r"(?is)</?%s\b[^>]*>" % BLOCK, "\n", doc)
    doc = re.sub(r"<[^>]+>", " ", doc)
    doc = html.unescape(doc).replace("\xa0", " ")
    doc = re.sub(r"[ \t]+", " ", doc)
    lines = [l.strip() for l in doc.split("\n")]
    out, blank = [], 0
    for l in lines:
        if not l:
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(l)
    return "\n".join(out).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="collector output; fetches every entry in it")
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--outdir", default="texts")
    ap.add_argument("--only", default=None,
                    help="comma-separated vids to fetch (subset of --json)")
    a = ap.parse_args()

    targets = []
    if a.json:
        d = json.load(open(a.json, encoding="utf-8"))
        keep = set(a.only.split(",")) if a.only else None
        for e in d["entries"]:
            if keep and e["vid"] not in keep:
                continue
            targets.append((e["vid"], e["url"], e.get("case", "")))
    for i, u in enumerate(a.url):
        targets.append(("url%d" % i, u, ""))

    os.makedirs(a.outdir, exist_ok=True)
    index, report = {}, []
    for vid, url, case in targets:
        path = os.path.join(a.outdir, "%s.txt" % vid)
        try:
            t = to_text(fetch(url))
            if len(t) < 400:
                raise RuntimeError("suspiciously short (%d chars) - blocked?" % len(t))
            open(path, "w", encoding="utf-8").write(t)
            index[vid] = {"file": os.path.abspath(path), "url": url,
                          "chars": len(t), "words": len(t.split()), "case": case}
            report.append("OK   %-10s %6d words  %s" % (vid, len(t.split()), case[:60]))
        except Exception as e:                       # noqa: BLE001
            index[vid] = {"file": None, "url": url, "error": str(e), "case": case}
            report.append("FAIL %-10s %s  (%s)" % (vid, case[:60], e))
        time.sleep(1.0)  # be polite to nevo

    json.dump(index, open(os.path.join(a.outdir, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("\n".join(report))
    print("\nindex: %s" % os.path.abspath(os.path.join(a.outdir, "index.json")))


if __name__ == "__main__":
    main()
