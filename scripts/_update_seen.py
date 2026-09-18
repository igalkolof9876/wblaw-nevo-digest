import json, os
from datetime import datetime, timezone

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
state = os.path.join(base, "state")

with open(os.path.join(state, "seen.json"), encoding="utf-8") as f:
    seen = json.load(f)

with open(os.path.join(state, "today.json"), encoding="utf-8") as f:
    today = json.load(f)

now_iso = datetime.now(timezone.utc).isoformat()
added = 0
for e in today.get("entries", []):
    vid = e["vid"]
    if vid not in seen:
        seen[vid] = {"date": e.get("issue_date", now_iso), "case": e.get("case", "")}
        added += 1

with open(os.path.join(state, "seen.json"), "w", encoding="utf-8") as f:
    json.dump(seen, f, ensure_ascii=False, indent=2)

pending_path = os.path.join(state, "pending.json")
if os.path.exists(pending_path):
    os.remove(pending_path)
    print("removed pending.json")
else:
    print("no pending.json to remove")

print("added", added, "vids to seen.json; total now", len(seen))
