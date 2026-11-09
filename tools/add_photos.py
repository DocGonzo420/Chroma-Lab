#!/usr/bin/env python3
"""Add new photos to Chroma Lab's built-in library.

1. Put the photo in photos/<id>.jpg (about 720px on the long side).
2. Add a row for it to data/photos.tsv (id, theme, title, tags, credit, license, source).
3. Run: python3 tools/add_photos.py

Photos already in data/library.json keep their palettes. New rows get a
6-color palette (k-means in Lab color space), and the library is written
back into index.html. A new theme also needs an entry in THEMES in index.html.
"""
import csv, json, os, re, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def lin(c):
    c=c/255.0; return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
def rgb2lab(rgb):
    R,G,B=[lin(rgb[:,i]) for i in range(3)]
    x=(R*0.4124564+G*0.3575761+B*0.1804375)/0.95047; y=R*0.2126729+G*0.7151522+B*0.0721750; z=(R*0.0193339+G*0.1191920+B*0.9503041)/1.08883
    f=lambda t: np.where(t>0.008856,np.cbrt(t),7.787*t+16/116)
    x,y,z=f(x),f(y),f(z); return np.stack([116*y-16,500*(x-y),200*(y-z)],1)
def lab2rgb(L,a,b):
    y=(L+16)/116; x=a/500+y; z=y-b/200
    f=lambda t: t**3 if t**3>0.008856 else (t-16/116)/7.787
    x=f(x)*0.95047; y=f(y); z=f(z)*1.08883
    un=lambda c: 255*(12.92*c if c<=0.0031308 else 1.055*c**(1/2.4)-0.055)
    r=[un(x*3.2404542-y*1.5371385-z*0.4985314),un(-x*0.9692660+y*1.8760108+z*0.0415560),un(x*0.0556434-y*0.2040259+z*1.0572252)]
    return [int(min(255,max(0,round(v)))) for v in r]
def kmeans(X,k,seed=7,iters=20):
    rng=np.random.default_rng(seed); m=len(X)
    C=[X[rng.integers(m)]]; D=np.full(m,np.inf)
    for _ in range(1,k):
        D=np.minimum(D,((X-C[-1])**2).sum(1)); p=D/D.sum(); C.append(X[rng.choice(m,p=p)])
    C=np.array(C)
    for _ in range(iters):
        d=((X[:,None,:]-C[None])**2).sum(2); A=d.argmin(1)
        newC=np.array([X[A==c].mean(0) if (A==c).any() else C[c] for c in range(k)])
        if np.allclose(newC,C,atol=0.05): C=newC; break
        C=newC
    cnt=np.bincount(A,minlength=k)/m
    return [(C[c],cnt[c]) for c in range(k) if cnt[c]>0]
def palette(img,k=6):
    w,h=img.size; r=min(1,(16000/(w*h))**0.5); sw,sh=max(1,round(w*r)),max(1,round(h*r))
    s=np.asarray(img.resize((sw,sh),Image.BILINEAR),dtype=np.float64).reshape(-1,3)
    X=rgb2lab(s)
    cands=sorted(kmeans(X,min(k*2+2,20)),key=lambda c:-c[1])
    chosen=[cands[0]]
    while len(chosen)<k and len(chosen)<len(cands):
        best=None;bs=-1
        for c in cands:
            if any(c is x for x in chosen): continue
            md=min(np.linalg.norm(x[0]-c[0]) for x in chosen); chroma=np.hypot(c[0][1],c[0][2])
            sc=(c[1]**0.35)*md*(1+chroma/120)
            if sc>bs: bs=sc;best=c
        chosen.append(best)
    L=np.array([c[0] for c in chosen]); d=((X[:,None,:]-L[None])**2).sum(2); A=d.argmin(1)
    out=[]
    for j in range(len(chosen)):
        share=float((A==j).mean()); idx=np.where(A==j)[0]
        p=int(idx[d[idx,j].argmin()]) if len(idx) else 0
        r,g,b=lab2rgb(*L[j])
        out.append({"hex":"#%02X%02X%02X"%(r,g,b),"share":round(share,4),"x":round(((p%sw)+0.5)/sw,4),"y":round(((p//sw)+0.5)/sh,4)})
    return sorted(out,key=lambda c:-c["share"])


def main():
    lib_path = os.path.join(ROOT, "data", "library.json")
    lib = json.load(open(lib_path, encoding="utf-8"))
    have = {it["id"] for it in lib}
    added = 0
    with open(os.path.join(ROOT, "data", "photos.tsv"), encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["id"] in have:
                continue
            path = os.path.join(ROOT, "photos", row["id"] + ".jpg")
            if not os.path.exists(path):
                sys.exit(f"Missing photo: photos/{row['id']}.jpg")
            im = Image.open(path).convert("RGB")
            lib.append({"id": row["id"], "theme": row["theme"], "title": row["title"],
                        "tags": [t.strip() for t in row["tags"].split(",") if t.strip()],
                        "credit": row["credit"], "license": row["license"], "source": row["source"],
                        "file": f"photos/{row['id']}.jpg", "w": im.size[0], "h": im.size[1],
                        "colors": palette(im, 6)})
            added += 1
    json.dump(lib, open(lib_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    page_path = os.path.join(ROOT, "index.html")
    page = open(page_path, encoding="utf-8").read()
    slim = json.loads(json.dumps(lib))
    for it in slim:
        for c in it["colors"]:
            c["share"] = round(c["share"], 3)
    s = page.index("const LIB=[")
    e = page.index(";\nconst THEMES", s)
    page = page[:s] + "const LIB=" + json.dumps(slim, ensure_ascii=False, separators=(",", ":")) + page[e:]
    open(page_path, "w", encoding="utf-8").write(page)

    tail = page[page.index("const THEMES="):]
    themes = set(re.findall(r'\["([a-z]+)","', tail[:tail.index(";")]))
    unknown = sorted({it["theme"] for it in lib} - themes)
    print(f"Added {added} photo(s). Library now has {len(lib)} photos.")
    if unknown:
        print("Add these themes to THEMES in index.html:", ", ".join(unknown))


if __name__ == "__main__":
    main()
