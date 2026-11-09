# Chroma Lab

A color palette reference you can use on your phone. Browse real photos with their palettes, or pull a palette from your own photo, and copy the codes.

## What it does

- **Explore:** 337 real photos in 34 searchable themes, each with a 6-color palette. Search by place, color word (like sage, rust or teal) or HEX code.
- **Moods:** search by 31 moods, like cozy, calm, moody, dreamy, earthy or neon, plus synonyms such as snug or serene. Tap a mood chip under the search box, or mix words like "cozy autumn". Each photo shows its top moods.
- **Studio:** load your own photo and pull 5 to 8 colors from it.
- **Codes:** HEX, RGB, HSL and CMYK for every color, with tap to copy.
- **Library:** save palettes and come back to them.
- **Cards:** make a printable reference card for any palette.

## Run it

Open `index.html` in a browser, or serve the folder with any static host such as GitHub Pages. Everything runs in the browser. Saved palettes stay in that browser's local storage.

The same app is also published as a Claude artifact. There it saves palettes to your Claude account instead.

## Files

- `index.html`: the whole app, with the photo library built in.
- `photos/`: the library photos, about 720px on the long side.
- `data/photos.tsv`: one row per photo, with theme, title, tags, credit, license and source.
- `data/library.json`: the same photos with their palettes.
- `tools/add_photos.py`: adds new photos to the library (needs Python 3 with numpy and Pillow).

## Add photos

1. Save the photo as `photos/<id>.jpg`.
2. Add its row to `data/photos.tsv`.
3. Run `python3 tools/add_photos.py`.

The script works out the new palettes and writes the library back into `index.html`. A new theme also needs an entry in `THEMES` in `index.html`. Moods are worked out in the browser from each palette's lightness, saturation, warmth and hues, so new photos get them automatically. The mood list is `MOODS` in `index.html`.

## Photo credits

The photos come from Wikimedia Commons under free licenses (CC BY, CC BY-SA, CC0 or public domain). Each photo keeps its own license, and the credits are in [CREDITS.md](CREDITS.md) and in the app. The GPL-3.0 license in this repo covers the code only.
