# -*- coding: utf-8 -*-
"""
Collect new Israeli judgments from Nevo's public daily digest (פד"י-מייל / פסיקה).

Pipeline:
  1. Read DailyMailArchive.aspx -> find פסיקה issues in the requested window
  2. Fetch each issue -> parse every judgment entry (case, court, judge, date,
     page count, abstract, Nevo topic path, full-text URL)
  3. Filter: page count > MIN_PAGES, and topic pre-classification
  4. Skip anything already processed (state file), so the 15:00 and 17:00
     runs never produce the same judgment twice.

Output: JSON to stdout (and --out file).

No login is required for any of these endpoints, but Nevo 403s non-browser
user agents, so a normal Chrome UA is mandatory.
"""
import re, os, sys, json, html, time, argparse, datetime as dt
from urllib.parse import unquote
import urllib.request, urllib.error

sys.stdout.reconfigure(encoding='utf-8')

BASE = "https://www.nevo.co.il"
ARCHIVE = BASE + "/DailyMailArchive.aspx"
MSG = BASE + "/Handlers/GetMsgContent.ashx?Msgid={}"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
}

MIN_PAGES = 4  # "מעל 3 עמודים"

# --- Topic routing -----------------------------------------------------------
# Nevo's own category label -> disposition.
# include  = squarely inside Igal's whitelist
# exclude  = squarely inside Igal's blacklist / outside the whitelist
# review   = Claude must read the abstract and decide (borderline or split topic)
INCLUDE = {
    "חוזים", "חברות", "ניירות ערך", "משפט מינהלי", "עבודה", "דיני עבודה",
    "ירושה", "ירושה וצוואות", "צוואות", "קניין", "מקרקעין", "דיון אזרחי",
    "בתי-משפט", "בתי משפט", "חדלות פירעון", "בוררות", "פטנטים",
    "סימני מסחר", "זכויות יוצרים", "קניין רוחני", "תאגידים", "שטרות",
    "מכרזים", "עמותות", "בנקאות", "ערבות", "עשיית עושר",
}
EXCLUDE = {
    "פלילי", "דין פלילי", "סדר דין פלילי", "תעבורה", "תכנון ובנייה",
    "תכנון ובניה", "ראיות", "בריאות", "הגנת הדייר", "פלת\"ד", "פיצויים לנפגעי תאונות דרכים",
    "בטיחות", "צבא", "בתי סוהר", "מעצרים", "עונשין",
}
# Categories that may or may not fall in the whitelist depending on the actual
# subject matter — Claude decides from the abstract.
REVIEW = {
    "נזיקין",            # in, unless bodily injury / פלת"ד
    "ביטוח",             # often a contract dispute -> חוזים
    "הוצאה לפועל",       # often civil procedure -> דיון אזרחי
    "רשויות מקומיות",    # often administrative -> משפט מינהלי
    "דיור ציבורי",
    "מסים", "מיסים",
    "ימאות",
    "משפט עברי",
    "משפחה",             # in only if it turns on ירושה/צוואות/קניין
    "עבודה - ביטוח לאומי",
    "ביטוח לאומי",
}

BODILY = ("נזק גוף", "נזקי גוף", "פלת\"ד", "פלתד", "תאונת דרכים", "תאונות דרכים",
          "נכות", "אחוזי נכות", "כאב וסבל", "תאונת עבודה", "רשלנות רפואית")


def fetch(url, retries=3, timeout=60):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("cp1255", errors="replace")
        except Exception as e:                      # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError("fetch failed %s: %s" % (url, last))


BLOCK = r"(?:td|tr|div|p|br|table|li|h[1-6])"


def txt(s):
    """HTML -> lines. Only block-level tags break a line; inline tags such as
    <b>/<a>/<span> are collapsed to a space, so a case line stays intact."""
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?is)</?%s\b[^>]*>" % BLOCK, "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return [l.strip() for l in s.split("\n") if l.strip()]


def find_issues(days_back):
    """Return [{'msgid','date','issue'}] for פסיקה issues within days_back days."""
    page = fetch(ARCHIVE)
    today = dt.date.today()
    cutoff = today - dt.timedelta(days=days_back)
    out, seen = [], set()
    # rows pair a date with several category links; walk row by row
    for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", page):
        dm = re.search(r"(\d{2})/(\d{2})/(\d{4})", row)
        if not dm:
            continue
        d = dt.date(int(dm.group(3)), int(dm.group(2)), int(dm.group(1)))
        if not (cutoff <= d <= today):
            continue
        # the פסיקה column is identified by the link id, not by cell text
        for a in re.findall(r"(?is)<a[^>]*linkPsika_\d+[^>]*>(?:.*?)</a>", row):
            mid = re.search(r"Msgid=(\d+)", a)
            if mid and mid.group(1) not in seen:
                seen.add(mid.group(1))
                iss = re.search(r"(\d+)", " ".join(txt(a)))
                out.append({"msgid": mid.group(1), "date": d.isoformat(),
                            "issue": iss.group(1) if iss else None})
    out.sort(key=lambda x: (x["date"], x["msgid"]))
    return out


CASE_RE = re.compile(
    r"^(?P<case>.{3,90}?)\s*\((?P<meta>[^()]{3,160}?;\s*\d{2}/\d{2}/\d{2})\)\s*-\s*(?P<pages>\d+)\s*ע"
)


def parse_issue(msgid):
    doc = fetch(MSG.format(msgid))
    chunks = re.split(r'name="verdictIndex_(\d+)"', doc)
    out, seen = [], set()
    for i in range(1, len(chunks), 2):
        vid, body, prev = chunks[i], chunks[i + 1], chunks[i - 1]
        if vid in seen:
            continue
        seen.add(vid)

        cats = re.findall(r"(?is)<b[^>]*>[^\[<]{0,25}\[([^\]<>]{2,40})\]", prev)
        cat = html.unescape(cats[-1]).strip() if cats else ""

        url = None
        m = re.search(r"https?://www\.nevo\.co\.il/psika_html/[^\"'&\s<>]+\.htm",
                      unquote(body[:6000]))
        if m:
            url = m.group(0)

        lines = txt(body[:6000])
        case = court = judge = date = abstract = topic_path = None
        pages = 0
        for j, ln in enumerate(lines):
            cm = CASE_RE.match(ln)
            if cm:
                case = cm.group("case").strip()
                meta = [p.strip() for p in cm.group("meta").split(";")]
                court = meta[0] if meta else None
                date = meta[-1] if meta else None
                judge = "; ".join(meta[1:-1]) if len(meta) > 2 else None
                pages = int(cm.group("pages"))
                rest = [x for x in lines[j + 1:] if len(x) > 15]
                if rest:
                    abstract = rest[0]
                # topic path line uses " - " separators, e.g. בתי-משפט - פומביות הדיון
                for cand in rest[1:4]:
                    if " - " in cand or "–" in cand:
                        topic_path = cand
                        break
                break
        if not case or not url:
            continue

        blob = " ".join(filter(None, [cat, topic_path, abstract, case]))
        if cat in EXCLUDE:
            disp, why = "exclude", "category in blacklist"
        elif cat in REVIEW:
            disp = "review"
            why = "borderline category"
            if cat == "נזיקין" and any(b in blob for b in BODILY):
                disp, why = "exclude", "tort appears to be bodily injury / פלת\"ד"
        elif cat in INCLUDE:
            disp, why = "include", "category in whitelist"
        else:
            disp, why = "review", "category not mapped"

        out.append({
            "vid": vid, "msgid": msgid, "case": case, "court": court,
            "judge": judge, "date": date, "pages": pages, "category": cat,
            "topic_path": topic_path, "abstract": abstract, "url": url,
            "disposition": disp, "reason": why,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days-back", type=int, default=1,
                    help="how many days of פסיקה issues to pull (default 1)")
    ap.add_argument("--state", default=os.path.expanduser(
        "~/.claude/skills/nevo-daily-digest/state/seen.json"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--min-pages", type=int, default=MIN_PAGES)
    ap.add_argument("--ignore-state", action="store_true")
    a = ap.parse_args()

    os.makedirs(os.path.dirname(a.state), exist_ok=True)
    seen = {}
    if os.path.exists(a.state) and not a.ignore_state:
        try:
            seen = json.load(open(a.state, encoding="utf-8"))
        except Exception:                            # noqa: BLE001
            seen = {}

    issues = find_issues(a.days_back)
    allrec, errors = [], []
    for iss in issues:
        try:
            allrec += [dict(r, issue_date=iss["date"]) for r in parse_issue(iss["msgid"])]
        except Exception as e:                       # noqa: BLE001
            errors.append({"msgid": iss["msgid"], "error": str(e)})

    fresh, dup, short = [], 0, 0
    for r in allrec:
        if r["vid"] in seen:
            dup += 1
            continue
        if r["pages"] < a.min_pages:
            short += 1
            continue
        fresh.append(r)

    res = {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "issues": issues,
        "stats": {"total_entries": len(allrec), "already_seen": dup,
                  "too_short": short, "candidates": len(fresh),
                  "include": sum(1 for r in fresh if r["disposition"] == "include"),
                  "review": sum(1 for r in fresh if r["disposition"] == "review"),
                  "excluded": sum(1 for r in fresh if r["disposition"] == "exclude")},
        "errors": errors,
        "entries": fresh,
    }
    out = json.dumps(res, ensure_ascii=False, indent=2)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(out)
    print(out)


if __name__ == "__main__":
    main()
