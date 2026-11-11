#!/usr/bin/env python3
"""Add a community photo by hand, for a photo someone sent you some other way.

Shared photos normally arrive as pull requests from the upload Worker, so you
only need this for photos you get by email or in person. For example:

  python3 tools/add_community.py --photo ~/Downloads/harbor.jpg \\
    --title "Morning fog over the harbor" --credit "Sam Lee" --license "CC BY 4.0" \\
    --palette "#1E2A33, #6B7F8C, #C9D3D8" --where "Halifax"

Only add a photo when its owner has agreed to share it under that license and
no one in it can be recognized, or everyone shown agreed.

The photo is resized to about 1200px on its long side and saved without its
metadata (so no location data). With --palette the given colors are kept and
measured on the photo; without it a 6-color palette is made. The script writes
photos/community/<id>.jpg and community/<id>.json, then rebuilds the list.
--remove <id> takes a photo out. Needs Python 3 with numpy and Pillow.
"""
import argparse, datetime, json, os, re, sys
import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_photos import ROOT, palette, rgb2lab  # same palette code as the library
import build_community

LICENSES = {"CC BY 4.0", "CC0 1.0"}
HEX = re.compile(r"#?([0-9a-fA-F]{6})\b")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "photo"


def measured(img, hexes):
    """Keep the given colors; measure how much of the photo each one covers."""
    w, h = img.size
    r = min(1, (16000 / (w * h)) ** 0.5)
    sw, sh = max(1, round(w * r)), max(1, round(h * r))
    X = rgb2lab(np.asarray(img.resize((sw, sh), Image.BILINEAR), dtype=np.float64).reshape(-1, 3))
    L = rgb2lab(np.array([[int(x[i:i + 2], 16) for i in (0, 2, 4)] for x in hexes], dtype=np.float64))
    d = ((X[:, None, :] - L[None]) ** 2).sum(2)
    A = d.argmin(1)
    out = []
    for j, x in enumerate(hexes):
        idx = np.where(A == j)[0]
        p = int(idx[d[idx, j].argmin()]) if len(idx) else int(d[:, j].argmin())
        out.append({"hex": "#" + x.upper(), "share": round(float((A == j).mean()), 4),
                    "x": round(((p % sw) + 0.5) / sw, 4), "y": round(((p // sw) + 0.5) / sh, 4)})
    return out


def main():
    ap = argparse.ArgumentParser(description="Add a community photo to Chroma Lab by hand.")
    ap.add_argument("--photo")
    ap.add_argument("--title")
    ap.add_argument("--credit", help="name to credit")
    ap.add_argument("--license", default="CC BY 4.0", help="CC BY 4.0 or CC0 1.0")
    ap.add_argument("--palette", default="", help="HEX codes, comma-separated (optional)")
    ap.add_argument("--where", default="", help="where it was taken (optional)")
    ap.add_argument("--tags", default="", help="comma-separated tags for search (optional)")
    ap.add_argument("--id", help="file name to use (default: made from the title)")
    ap.add_argument("--remove", metavar="ID", help="take a community photo out")
    a = ap.parse_args()

    if a.remove:
        for f in (os.path.join(ROOT, "community", a.remove + ".json"),
                  os.path.join(ROOT, "photos", "community", a.remove + ".jpg")):
            if os.path.exists(f):
                os.remove(f)
        build_community.main()
        return

    for need in ("photo", "title", "credit"):
        if not getattr(a, need):
            ap.error(f"--{need} is required")
    if a.license not in LICENSES:
        ap.error("--license must be " + " or ".join(sorted(LICENSES)))

    im = ImageOps.exif_transpose(Image.open(os.path.expanduser(a.photo))).convert("RGB")
    im.thumbnail((1200, 1200), Image.LANCZOS)
    pid = slug(a.id or a.title)
    os.makedirs(os.path.join(ROOT, "photos", "community"), exist_ok=True)
    im.save(os.path.join(ROOT, "photos", "community", pid + ".jpg"), "JPEG", quality=85, optimize=True, progressive=True)

    hexes = list(dict.fromkeys(m.upper() for m in HEX.findall(a.palette)))[:10]
    entry = {"id": pid, "title": a.title.strip(), "credit": a.credit.strip(), "license": a.license,
             "where": a.where.strip(), "tags": [t.strip() for t in a.tags.split(",") if t.strip()],
             "w": im.size[0], "h": im.size[1], "colors": measured(im, hexes) if hexes else palette(im, 6),
             "submitted": datetime.date.today().isoformat()}
    json.dump(entry, open(os.path.join(ROOT, "community", pid + ".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    build_community.main()


if __name__ == "__main__":
    main()
