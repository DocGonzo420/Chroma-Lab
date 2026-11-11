#!/usr/bin/env python3
"""Add an approved community photo to Chroma Lab.

People share photos from the app through a GitHub issue (the "Community photo"
form). To approve one:

1. Download the photo attached to the issue.
2. Run, for example:
     python3 tools/add_community.py --issue 12 --photo ~/Downloads/harbor.jpg \\
       --title "Morning fog over the harbor" --credit "Sam Lee" --license "CC BY 4.0" \\
       --palette "#1E2A33, #6B7F8C, #C9D3D8" --where "Halifax"
3. Open a pull request with the changes and merge it. Then close the issue.

The photo is resized to about 960px on its long side and saved without its
metadata (so no location data). With --palette, the shared colors are kept and
their shares are measured on the photo; without it, a fresh 6-color palette is
made. The script writes photos/community/<id>.jpg, data/community.json, the
COMMUNITY list in index.html and the Community section of CREDITS.md.
Run it again with the same --id (or title) to replace an entry, or with
--remove <id> to take one out.
"""
import argparse, json, os, re, sys
import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_photos import ROOT, palette, rgb2lab  # same palette code as the library

REPO = "DocGonzo420/Chroma-Lab"
LICENSES = {"CC BY 4.0", "CC0 1.0"}
HEX = re.compile(r"#?([0-9a-fA-F]{6})\b")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48] or "photo"


def measured(img, hexes):
    """Keep the shared colors; measure how much of the photo each one covers."""
    w, h = img.size
    r = min(1, (16000 / (w * h)) ** 0.5)
    sw, sh = max(1, round(w * r)), max(1, round(h * r))
    X = rgb2lab(np.asarray(img.resize((sw, sh), Image.BILINEAR), dtype=np.float64).reshape(-1, 3))
    rgb = np.array([[int(x[i:i + 2], 16) for i in (0, 2, 4)] for x in hexes], dtype=np.float64)
    L = rgb2lab(rgb)
    d = ((X[:, None, :] - L[None]) ** 2).sum(2)
    A = d.argmin(1)
    out = []
    for j, x in enumerate(hexes):
        idx = np.where(A == j)[0]
        p = int(idx[d[idx, j].argmin()]) if len(idx) else int(d[:, j].argmin())
        out.append({"hex": "#" + x.upper(), "share": round(float((A == j).mean()), 4),
                    "x": round(((p % sw) + 0.5) / sw, 4), "y": round(((p // sw) + 0.5) / sh, 4)})
    return out


def write_all(items):
    json.dump(items, open(os.path.join(ROOT, "data", "community.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    slim = json.loads(json.dumps(items))
    for it in slim:
        for c in it["colors"]:
            c["share"] = round(c["share"], 3)
    page_path = os.path.join(ROOT, "index.html")
    page = open(page_path, encoding="utf-8").read()
    s = page.index("const COMMUNITY=")
    e = page.index(";/* community photos", s)
    page = page[:s] + "const COMMUNITY=" + json.dumps(slim, ensure_ascii=False, separators=(",", ":")) + page[e:]
    open(page_path, "w", encoding="utf-8").write(page)

    cred_path = os.path.join(ROOT, "CREDITS.md")
    cred = open(cred_path, encoding="utf-8").read()
    head = "## Community"
    s = cred.index(head)
    e = cred.find("\n## ", s + len(head))
    e = len(cred) if e < 0 else e
    intro = ("Photos shared by Chroma Lab users through the Community photo form. "
             "Each person confirmed they took the photo or own the rights to it.\n")
    lines = [f"- **{it['title']}**: {it['credit']}, {it['license']}. [Source]({it['source']})" for it in items]
    body = head + "\n\n" + intro + "\n" + ("\n".join(lines) if lines else "None yet.") + "\n"
    cred = cred[:s] + body + cred[e:]
    open(cred_path, "w", encoding="utf-8").write(cred)


def main():
    ap = argparse.ArgumentParser(description="Add an approved community photo to Chroma Lab.")
    ap.add_argument("--photo", help="the photo attached to the issue")
    ap.add_argument("--title")
    ap.add_argument("--credit", help="name to credit, as given on the form")
    ap.add_argument("--license", default="CC BY 4.0", help="CC BY 4.0 or CC0 1.0")
    ap.add_argument("--issue", type=int, help="the GitHub issue number it came in on")
    ap.add_argument("--palette", default="", help="the HEX codes from the form")
    ap.add_argument("--where", default="", help="where it was taken (optional)")
    ap.add_argument("--tags", default="", help="comma-separated tags for search (optional)")
    ap.add_argument("--id", help="file name to use (default: made from the title)")
    ap.add_argument("--remove", metavar="ID", help="take a community photo out")
    a = ap.parse_args()

    path = os.path.join(ROOT, "data", "community.json")
    items = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []

    if a.remove:
        items = [it for it in items if it["id"] != a.remove]
        f = os.path.join(ROOT, "photos", "community", a.remove + ".jpg")
        if os.path.exists(f):
            os.remove(f)
        write_all(items)
        print(f"Removed {a.remove}. Community now has {len(items)} photo(s).")
        return

    for need in ("photo", "title", "credit", "issue"):
        if not getattr(a, need):
            ap.error(f"--{need} is required")
    if a.license not in LICENSES:
        ap.error("--license must be " + " or ".join(sorted(LICENSES)))

    im = ImageOps.exif_transpose(Image.open(os.path.expanduser(a.photo))).convert("RGB")
    im.thumbnail((960, 960), Image.LANCZOS)
    pid = slug(a.id or a.title)
    out = os.path.join(ROOT, "photos", "community", pid + ".jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out, "JPEG", quality=85, optimize=True, progressive=True)  # saved without EXIF or GPS

    hexes = list(dict.fromkeys(m.upper() for m in HEX.findall(a.palette)))[:12]
    colors = measured(im, hexes) if hexes else palette(im, 6)
    item = {"id": pid, "theme": "community", "title": a.title.strip(), "credit": a.credit.strip(),
            "license": a.license, "source": f"https://github.com/{REPO}/issues/{a.issue}",
            "where": a.where.strip(), "tags": [t.strip() for t in a.tags.split(",") if t.strip()],
            "file": f"photos/community/{pid}.jpg", "w": im.size[0], "h": im.size[1], "colors": colors}
    items = [it for it in items if it["id"] != pid] + [item]
    write_all(items)
    print(f"Added {pid} ({len(colors)} colors). Community now has {len(items)} photo(s).")


if __name__ == "__main__":
    main()
