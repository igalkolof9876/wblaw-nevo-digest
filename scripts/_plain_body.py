import json, os

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
state = os.path.join(base, "state")

with open(os.path.join(state, "analyses.json"), encoding="utf-8") as f:
    d = json.load(f)

lines = []
lines.append(f"סקירת פסיקה יומית - {d['date']} ({len(d['items'])} פסקי דין)")
lines.append("")
lines.append("לצפייה בסקירה המלאה (כולל ניתוח מלא לכל פסק דין):")
lines.append("https://claude.ai/code/artifact/6f480aa3-2cad-4591-94dd-2f0cb88981d9")
lines.append("")
lines.append("פסקי הדין בגיליון היום:")
for it in d["items"]:
    lines.append(f"- {it['case']} ({it['topic']})")
lines.append("")
lines.append("הופק אוטומטית מגיליון פד\"י-מייל (פסיקה) של נבו. תמצית עבודה - אינה תחליף לקריאת פסק הדין במלואו או לייעוץ משפטי.")

with open(os.path.join(state, "plain_body.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("OK", len(lines), "lines")
