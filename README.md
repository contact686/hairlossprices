# Hair Loss Price Index

A comparison site for US hair-loss telehealth providers, generated from one data file.

- `data/providers.json` — every provider, price, term and source. **This is the site.** Edit this, nothing else, to change prices.
- `data/changelog.json` — the public log. The monthly check appends to it automatically.
- `data/site.json` — site name, domain, contact email. Change `base_url` to your real address before launch.
- `build.py` — turns the data into `dist/` (110 pages at launch: home, 12 provider pages, 66 head-to-heads, 9 cheapest-by-treatment pages, women, cancel pages, states, policies, sitemap).
- `scripts/verify.py` — the monthly price re-check. Fetches each source page, looks for the price on file, logs misses to the changelog. Never changes a price silently.
- `.github/workflows/build.yml` — builds and publishes on every change, and runs the price check on the 1st of each month.

## Put it live on GitHub Pages (free, no terminal)

1. Create a free account at github.com.
2. New repository → name it exactly `YOUR-USERNAME.github.io` → Public → Create.
3. Easiest upload: install **GitHub Desktop** (free), choose *File → Add local repository*, pick this folder, then *Publish repository*. (The web uploader works too: *Add file → Upload files*, drag everything in, including the hidden `.github` folder — check it arrived.)
4. In the repository: *Settings → Pages → Source: GitHub Actions*.
5. Open the *Actions* tab. The first run takes about a minute. When it's green, the site is at `https://YOUR-USERNAME.github.io`.
6. Edit `data/site.json` → `base_url` to that address (or your custom domain later) and commit. Every commit rebuilds the site.

Custom domain later: buy the domain, add it under *Settings → Pages → Custom domain*, and set `base_url` to it.

## Updating a price

Open `data/providers.json` on GitHub, click the pencil, change the number and the `note`, set `"status": "verified"` if you confirmed it at checkout, commit. The site rebuilds itself.

## Adding an article

Save it as `content/articles/your-slug.html`. First line:

    <!-- title: Oral minoxidil online in 2026 | date: 2026-09-01 | description: One sentence for search results. -->

followed by the article as HTML paragraphs. It appears at `/blog/your-slug/` and on `/blog/` on the next build.

## Adding a provider

Copy any provider block in `providers.json`, change every field, keep the `slug` lowercase-with-dashes. All comparison, cheapest and cancel pages for it are generated automatically.

## Tracking which pages convert

Every partner button automatically adds `subid=<page>-<placement>` to the affiliate link (for example `subid=reviews-hims-review` or `subid=cheapest-oral-finasteride-cheapest`), so the network's dashboard tells you which page and which button earned each signup. If a network uses a different parameter name, set `"subid_param"` inside that provider's `affiliate` block.

## Analytics and newsletter

`data/site.json` has two empty slots: paste an analytics snippet (Cloudflare Web Analytics is free and cookie-free; Google Analytics works too) into `analytics_head`, and a form embed from an email service (Buttondown, Kit, Mailchimp) into `newsletter_embed`. Both appear on the next build; the newsletter box only shows once it has something in it.

## Adding affiliate links

When a network approves you, paste the tracking link into that provider's `"affiliate": {"url": ...}`. Buttons switch to it; nothing else changes.

## Run it on your own computer (optional)

    pip install jinja2 requests
    python build.py        # writes dist/
    open dist/index.html   # or double-click it
