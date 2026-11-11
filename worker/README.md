# Community upload Worker

This small Cloudflare Worker lets anyone share a photo from Chroma Lab without an account. It checks the Turnstile token (blocks bots), checks the photo (JPEG, at most 1 MB and 1600 pixels), removes its metadata (location data included), and opens one pull request per photo in this repo. Merging the pull request approves the photo.

Everything here fits Cloudflare's free plan.

## Set it up (once, about 15 minutes)

### 1. Cloudflare account
Sign up at dash.cloudflare.com. The free plan is enough, and no domain is needed.

### 2. Turnstile widget (the bot check)
1. In the Cloudflare dashboard, open **Turnstile** and press **Add widget**.
2. Name: `Chroma Lab`. Hostname: `docgonzo420.github.io`. Widget mode: **Managed**.
3. Keep the **Site key** (public) and the **Secret key** (private) for the next steps.

### 3. GitHub token (lets the Worker open pull requests, nothing else)
1. On GitHub: **Settings › Developer settings › Personal access tokens › Fine-grained tokens › Generate new token**.
2. Name: `Chroma Lab community`. Expiration: 1 year (set a reminder to renew it).
3. **Repository access: Only select repositories › DocGonzo420/Chroma-Lab.**
4. **Repository permissions:** Contents **Read and write**, Pull requests **Read and write**. Leave everything else at No access.
5. Generate it and copy it. It's shown only once. Don't paste it anywhere except step 4 below.

### 4. The Worker
1. In the Cloudflare dashboard: **Workers & Pages › Create › Create Worker**. Name it `chroma-lab-community` and press **Deploy**.
2. Press **Edit code**, replace everything with the contents of `worker/index.js`, and press **Deploy**.
3. Open the Worker's **Settings › Variables and Secrets** and add:
   - `GITHUB_TOKEN`, type **Secret**: the token from step 3.
   - `TURNSTILE_SECRET`, type **Secret**: the Turnstile secret key.
   - `REPO`, type **Text**: `DocGonzo420/Chroma-Lab`
   - `ALLOWED_ORIGINS`, type **Text**: `https://docgonzo420.github.io`
4. Copy the Worker's address, like `https://chroma-lab-community.<your-name>.workers.dev`. Opening it in a browser should show `"ok":true`.

### 5. Turn sharing on in the app
Put the Worker's address in `COMMUNITY_API` and the Turnstile **site key** in `TURNSTILE_SITEKEY` near the top of the script in `index.html`. Both are public, so they're safe in the page. The Share to Community button appears once both are set.

### 6. Let the Action update the list after a merge
In the repo: **Settings › Actions › General › Workflow permissions** › **Read and write permissions** › Save. The workflow in `.github/workflows/community.yml` uses this to commit the rebuilt Community list after you merge a photo.

## Approving photos
Each shared photo arrives as a pull request named "Community photo: <title>" with the photo shown in it.
- **Approve:** merge it. A minute later it's under the Community filter on the site.
- **Turn down:** close it and press **Delete branch**.

## Limits and notes
- Photos are sent at up to 1200 pixels on the long side, usually 200 to 400 KB. The Worker refuses anything over 1 MB or 1600 pixels, and anything that isn't a JPEG.
- The sharer's title, name and optional place are public in the pull request. The app says so before they send.
- To stop new submissions at any time, delete the Worker or remove `GITHUB_TOKEN` from it.
- Using wrangler instead of the dashboard: `cd worker && npx wrangler deploy`, then `npx wrangler secret put GITHUB_TOKEN` and `npx wrangler secret put TURNSTILE_SECRET`. `wrangler.toml` already has the two text settings.
