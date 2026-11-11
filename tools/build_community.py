#!/usr/bin/env python3
"""Rebuild Chroma Lab's Community list from community/*.json.

Each approved community photo is two files: photos/community/<id>.jpg and
community/<id>.json (title, credit, license, place, size, palette). Shared
photos arrive that way as pull requests from the upload Worker (worker/), and
tools/add_community.py adds one by hand the same way.

This script writes data/community.json, the COMMUNITY list in index.html and
the Community section of CREDITS.md. A GitHub Action runs it after every merge
that touches community/, so merging a pull request is all approval takes.
Needs only Python 3.
"""
import glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "DocGonzo420/Chroma-Lab"
HEX = re.compile(r"^#[0-9A-F]{6}$")


def load():
    items = []
    for path in sorted(glob.glob(os.path.join(ROOT, "community", "*.json"))):
        e = json.load(open(path, encoding="utf-8"))
        pid = os.path.splitext(os.path.basename(path))[0]
        if not os.path.exists(os.path.join(ROOT, "photos", "community", pid + ".jpg")):
            print(f"Skipping {pid}: photos/community/{pid}.jpg is missing")
            continue
        colors = [{"hex": c["hex"].upper(), "share": c.get("share"), "x": c.get("x"), "y": c.get("y")}
                  for c in e.get("colors", []) if HEX.match(str(c.get("hex", "")).upper())]
        if not colors:
            print(f"Skipping {pid}: no palette")
            continue
        for c in colors:
            for k in ("share", "x", "y"):
                if c[k] is not None:
                    c[k] = round(float(c[k]), 3)
        items.append({"id": pid, "theme": "community", "title": e["title"], "credit": e["credit"],
                      "license": e["license"], "where": e.get("where", ""),
                      "source": f"https://github.com/{REPO}/blob/main/photos/community/{pid}.jpg",
                      "tags": e.get("tags", []), "file": f"photos/community/{pid}.jpg",
                      "w": e.get("w", 3), "h": e.get("h", 2), "colors": colors,
                      "submitted": e.get("submitted", "")})
    items.sort(key=lambda it: (it["submitted"], it["id"]), reverse=True)  # newest first
    return items


def write(items):
    json.dump(items, open(os.path.join(ROOT, "data", "community.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    page_path = os.path.join(ROOT, "index.html")
    page = open(page_path, encoding="utf-8").read()
    s = page.index("const COMMUNITY=")
    e = page.index(";/* community photos", s)
    page = page[:s] + "const COMMUNITY=" + json.dumps(items, ensure_ascii=False, separators=(",", ":")) + page[e:]
    open(page_path, "w", encoding="utf-8").write(page)

    cred_path = os.path.join(ROOT, "CREDITS.md")
    cred = open(cred_path, encoding="utf-8").read()
    head = "## Community"
    s = cred.index(head)
    e = cred.find("\n## ", s + len(head))
    e = len(cred) if e < 0 else e
    intro = ("Photos shared by Chroma Lab users. Each person confirmed they took the photo "
             "or own the rights to it, and chose its license.\n")
    lines = [f"- **{it['title']}**: {it['credit']}, {it['license']}. [Source]({it['source']})" for it in items]
    cred = cred[:s] + head + "\n\n" + intro + "\n" + ("\n".join(lines) if lines else "None yet.") + "\n" + cred[e:]
    open(cred_path, "w", encoding="utf-8").write(cred)


def main():
    items = load()
    write(items)
    print(f"Community has {len(items)} photo(s).")


if __name__ == "__main__":
    main()
