/* Chroma Lab community uploads.
 *
 * The app posts a photo, its palette and the sharer's choices here. No account is needed.
 * This Worker checks the Cloudflare Turnstile token (blocks bots), checks the photo,
 * strips its metadata (location data included), and opens one pull request per photo in
 * the repo. Nothing shows in the app until the owner merges that pull request.
 *
 * Settings (Cloudflare dashboard > the Worker > Settings > Variables and Secrets):
 *   GITHUB_TOKEN      secret. Fine-grained token for this one repo only:
 *                     Contents read and write, Pull requests read and write.
 *   TURNSTILE_SECRET  secret. The Turnstile widget's secret key.
 *   REPO              text, e.g. DocGonzo420/Chroma-Lab
 *   ALLOWED_ORIGINS   text, comma-separated sites allowed to send photos,
 *                     e.g. https://docgonzo420.github.io
 */

const MAX_BYTES = 1_000_000;          // the app sends about 300 KB; refuse anything over 1 MB
const MAX_EDGE = 1600;                // the app sends at most 1200 px on the long side
const LICENSES = ["CC BY 4.0", "CC0 1.0"];
const HEX = /^#[0-9A-F]{6}$/;

export default {
  async fetch(req, env) {
    const origin = req.headers.get("Origin") || "";
    const allowed = (env.ALLOWED_ORIGINS || "").split(",").map(s => s.trim()).filter(Boolean);
    const cors = allowed.includes(origin)
      ? { "Access-Control-Allow-Origin": origin, "Vary": "Origin" } : {};
    const reply = (status, body) => new Response(JSON.stringify(body), {
      status, headers: { "Content-Type": "application/json", ...cors } });

    if (req.method === "OPTIONS") {
      return new Response(null, { status: cors["Access-Control-Allow-Origin"] ? 204 : 403, headers: {
        ...cors, "Access-Control-Allow-Methods": "POST", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400" } });
    }
    const path = new URL(req.url).pathname;
    if (req.method === "GET" && path === "/") return reply(200, { ok: true, service: "Chroma Lab community uploads" });
    if (req.method !== "POST" || path !== "/submit") return reply(404, { error: "Not found." });
    if (!cors["Access-Control-Allow-Origin"]) return reply(403, { error: "Sharing only works from the Chroma Lab site." });
    if (+(req.headers.get("Content-Length") || 0) > MAX_BYTES + 50_000) return reply(413, { error: "That photo is too large." });

    let form;
    try { form = await req.formData(); } catch { return reply(400, { error: "That upload couldn't be read." }); }

    // 1. Turnstile: one human check per submission
    const token = form.get("cf-turnstile-response");
    if (!token) return reply(400, { error: "Please finish the check first." });
    const tv = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST", body: new URLSearchParams({ secret: env.TURNSTILE_SECRET, response: token,
        remoteip: req.headers.get("CF-Connecting-IP") || "" }) }).then(r => r.json()).catch(() => ({}));
    const hosts = allowed.map(o => { try { return new URL(o).hostname; } catch { return ""; } });
    if (!tv.success || (tv.hostname && !hosts.includes(tv.hostname))) {
      return reply(403, { error: "The check didn't pass. Please try again." });
    }

    // 2. The details
    let m;
    try { m = JSON.parse(form.get("meta") || "{}"); } catch { return reply(400, { error: "That upload couldn't be read." }); }
    const err = checkMeta(m);
    if (err) return reply(400, { error: err });

    // 3. The photo: a JPEG within the size limits, saved without metadata
    const file = form.get("photo");
    if (!file || typeof file.arrayBuffer !== "function") return reply(400, { error: "The photo is missing." });
    if (file.size > MAX_BYTES) return reply(413, { error: "That photo is too large." });
    const jpg = cleanJpeg(new Uint8Array(await file.arrayBuffer()));
    if (jpg.error) return reply(400, { error: jpg.error });

    // 4. One pull request with the photo and its details
    const id = slug(m.title) + "-" + crypto.randomUUID().slice(0, 6);
    const entry = {
      id, title: m.title.trim(), credit: m.credit.trim(), license: m.license, where: (m.where || "").trim(),
      w: jpg.width, h: jpg.height, colors: m.colors, submitted: new Date().toISOString().slice(0, 10),
    };
    try {
      const pr = await openPullRequest(env, id, jpg.bytes, entry);
      return reply(200, { ok: true, id, pr });
    } catch (e) {
      console.log("github error", e && e.message);
      return reply(502, { error: "Your photo couldn't be sent just now. Please try again later." });
    }
  },
};

function checkMeta(m) {
  const text = (v, max) => typeof v === "string" && v.trim().length > 0 && v.length <= max;
  if (!text(m.title, 60)) return "Give the photo a title.";
  if (!text(m.credit, 60)) return "Add the name to credit.";
  if (m.where != null && (typeof m.where !== "string" || m.where.length > 60)) return "The place is too long.";
  if (!LICENSES.includes(m.license)) return "Pick a license.";
  if (m.owns !== true || m.people !== true || m.agree !== true) return "Tick all three boxes to share.";
  if (!Array.isArray(m.colors) || m.colors.length < 1 || m.colors.length > 10) return "The palette is missing.";
  for (const c of m.colors) {
    if (!c || typeof c.hex !== "string" || !HEX.test(c.hex)) return "The palette has a bad color code.";
    for (const k of ["share", "x", "y"]) if (c[k] != null && !(typeof c[k] === "number" && c[k] >= 0 && c[k] <= 1)) return "The palette has a bad value.";
  }
  m.colors = m.colors.map(c => ({ hex: c.hex, share: round(c.share), x: round(c.x), y: round(c.y) }));
  return "";
}
const round = v => (v == null ? null : Math.round(v * 10000) / 10000);
const slug = s => s.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "photo";

/* Walk the JPEG's segments: keep what the image needs, drop EXIF, XMP, comments and other
 * metadata (APP1 to APP15, COM), and read its size from the frame header. */
function cleanJpeg(b) {
  if (b.length < 4 || b[0] !== 0xFF || b[1] !== 0xD8) return { error: "Send the photo as a JPEG." };
  const keep = [b.subarray(0, 2)];
  let i = 2, width = 0, height = 0;
  while (i + 4 <= b.length) {
    if (b[i] !== 0xFF) return { error: "That photo couldn't be read." };
    const mk = b[i + 1];
    if (mk === 0xFF) { i++; continue; }
    const len = (b[i + 2] << 8) | b[i + 3];
    if (len < 2 || i + 2 + len > b.length) return { error: "That photo couldn't be read." };
    if (mk >= 0xC0 && mk <= 0xCF && mk !== 0xC4 && mk !== 0xC8 && mk !== 0xCC) {
      height = (b[i + 5] << 8) | b[i + 6]; width = (b[i + 7] << 8) | b[i + 8];
    }
    const meta = (mk >= 0xE1 && mk <= 0xEF) || mk === 0xFE;
    if (!meta) keep.push(b.subarray(i, i + 2 + len));
    i += 2 + len;
    if (mk === 0xDA) { keep.push(b.subarray(i)); break; }   // image data runs to the end
  }
  if (!width || !height) return { error: "That photo couldn't be read." };
  if (width > MAX_EDGE || height > MAX_EDGE) return { error: "That photo is too large." };
  const out = new Uint8Array(keep.reduce((n, p) => n + p.length, 0));
  let o = 0; for (const p of keep) { out.set(p, o); o += p.length; }
  return { bytes: out, width, height };
}

const b64 = bytes => { let s = ""; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000)); return btoa(s); };

async function gh(env, method, path, body) {
  const r = await fetch(`https://api.github.com/repos/${env.REPO}${path}`, {
    method, body: body ? JSON.stringify(body) : undefined,
    headers: { Authorization: `Bearer ${env.GITHUB_TOKEN}`, Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "chroma-lab-community", "Content-Type": "application/json" } });
  if (!r.ok) throw new Error(`${method} ${path}: ${r.status}`);
  return r.json();
}

/* One commit on a new branch with both files, then a pull request for it. */
async function openPullRequest(env, id, jpg, entry) {
  const repo = await gh(env, "GET", "");
  const base = repo.default_branch;
  const head = await gh(env, "GET", `/git/ref/heads/${base}`);
  const parent = await gh(env, "GET", `/git/commits/${head.object.sha}`);
  const photo = await gh(env, "POST", "/git/blobs", { content: b64(jpg), encoding: "base64" });
  const json = await gh(env, "POST", "/git/blobs", { content: JSON.stringify(entry, null, 1) + "\n", encoding: "utf-8" });
  const tree = await gh(env, "POST", "/git/trees", { base_tree: parent.tree.sha, tree: [
    { path: `photos/community/${id}.jpg`, mode: "100644", type: "blob", sha: photo.sha },
    { path: `community/${id}.json`, mode: "100644", type: "blob", sha: json.sha } ] });
  const commit = await gh(env, "POST", "/git/commits", {
    message: `Community photo: ${entry.title}\n\nShared by ${entry.credit} under ${entry.license}.`,
    tree: tree.sha, parents: [head.object.sha] });
  const branch = `community/${id}`;
  await gh(env, "POST", "/git/refs", { ref: `refs/heads/${branch}`, sha: commit.sha });
  const sw = entry.colors.map(c => c.hex).join(", ");
  const pr = await gh(env, "POST", "/pulls", { head: branch, base, title: `Community photo: ${entry.title}`,
    body: [`**${entry.title}** by ${entry.credit}${entry.where ? `, ${entry.where}` : ""}`, "",
      `License: ${entry.license}. Size: ${entry.w} × ${entry.h}. Palette: ${sw}`, "",
      `![${entry.title}](https://github.com/${env.REPO}/blob/${branch}/photos/community/${id}.jpg?raw=true)`, "",
      "The sharer confirmed they took the photo or own the rights to it, that no one in it can be recognized or everyone shown agreed, and that Chroma Lab may show it under this license.", "",
      "Merge to add it to the Community filter. Close the pull request and delete its branch to turn it down."].join("\n") });
  return pr.number;
}
