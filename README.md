# Chroma Lab

A color palette reference you can use on your phone. Browse real photos with their palettes, or pull a palette from your own photo, and copy the codes.

## What it does

- **Explore:** 413 real photos in 44 searchable themes, each with a 6-color palette. Search by place, color word (like sage, rust or teal) or HEX code.
- **Moods:** search by 43 moods, like cozy, calm, moody, dreamy, earthy, neon, coastal or boho, plus synonyms such as snug or serene. Tap a mood chip under the search box, or mix words like "cozy autumn". Each photo shows its top moods.
- **Studio:** load your own photo and pull 5 to 8 colors from it.
- **Codes:** HEX, RGB, HSL and CMYK for every color, with tap to copy.
- **Library:** save palettes and come back to them.
- **Cards:** make a printable reference card for any palette.
- **Random:** tap **Random** in Explore to open a random palette from the photos you're looking at.
- **Today:** the Today tab shows a Palette of the Day, the same for everyone on a given date, plus the past week's picks.
- **Install:** tap **Install** at the top to add Chroma Lab to the home screen. It then opens like an app and works offline for photos you've already viewed.

## Run it

Open `index.html` in a browser, or serve the folder with any static host such as GitHub Pages. Everything runs in the browser. Saved palettes stay in that browser's local storage.

The same app is also published as a Claude artifact. There it saves palettes to your Claude account instead.

## Files

- `index.html`: the whole app, with the photo library built in.
- `photos/`: the library photos, about 720px on the long side.
- `data/photos.tsv`: one row per photo, with theme, title, tags, credit, license and source.
- `data/library.json`: the same photos with their palettes.
- `manifest.webmanifest`, `sw.js` and `icons/`: let phones install the site as an app and keep it working offline.
- `tools/add_photos.py`: adds new photos to the library (needs Python 3 with numpy and Pillow).
- `photos/community/` and `data/community.json`: approved community photos.
- `tools/add_community.py`: adds an approved community photo.
- `.github/ISSUE_TEMPLATE/community-photo.yml`: the form people fill in to share a photo.

## Add photos

1. Save the photo as `photos/<id>.jpg`.
2. Add its row to `data/photos.tsv`.
3. Run `python3 tools/add_photos.py`.

The script works out the new palettes and writes the library back into `index.html`. A new theme also needs an entry in `THEMES` in `index.html`. Moods are worked out in the browser from each palette's lightness, saturation, warmth and hues, so new photos get them automatically. The mood list is `MOODS` in `index.html`.

## Community photos

Anyone can share a photo they took. In Studio, after pulling a palette from their own photo, they tap **Share to Community**. The app asks for a title, the name to credit and a license (CC BY 4.0 or CC0), and has them confirm three things: they took the photo or own the rights, no one in it can be recognized or everyone agreed, and Chroma Lab may show it under that license. It then saves the photo and opens the **Community photo** form on GitHub with everything filled in, where they attach the photo. Sharing needs a free GitHub account, and the post is public while it's reviewed.

Nothing goes into the app until you approve it:

1. Look at the issue. Close it if it's spam, not a real photo, or shows people who didn't agree.
2. Download the attached photo and run `python3 tools/add_community.py` with the details from the issue (`--help` shows an example).
3. Open a pull request with the changes, merge it, and close the issue.

The script resizes the photo, removes its location data, keeps the shared palette and writes the credit into the app and CREDITS.md. In the app, approved photos show under the **Community** filter in Explore. `--remove <id>` takes one out.

## Photo credits

The library photos come from Wikimedia Commons under free licenses (CC BY, CC BY-SA, CC0 or public domain). Community photos are shared by their photographers under CC BY 4.0 or CC0. Each photo keeps its own license, and the credits are in [CREDITS.md](CREDITS.md) and in the app. The GPL-3.0 license in this repo covers the code only.
