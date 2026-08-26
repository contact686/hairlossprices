#!/usr/bin/env python3
"""Build the Hair Loss Price Index.

Everything on the site is generated from data/providers.json. Run:

    python build.py            # writes the finished site to dist/

Links are relative, so the output works on GitHub Pages (root or /repo/),
on a custom domain, or opened straight from the dist/ folder.
"""
import json
import os
import posixpath
import shutil
from datetime import date
from itertools import combinations
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
DATA = ROOT / "data"
TEMPLATES = ROOT / "templates"
CONTENT = ROOT / "content"

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

STATUS_LABEL = {
    "verified": "Checked at checkout",
    "published": "From the provider's published price; checkout check pending",
    "conflicting": "Sources disagree; checkout check pending",
    "unknown": "Not published",
}


def load_json(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


def nice_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return date(y, m, d).strftime("%-d %b %Y")


def money(v):
    return f"${v:,.0f}" if isinstance(v, (int, float)) else "—"


def build_index(data):
    """Attach derived fields: per-format cheapest provider, provider anchor price, rank."""
    formats = data["formats"]
    providers = data["providers"]
    cheapest = {}
    for fmt in formats:
        key = fmt["key"]
        best = None
        for p in providers:
            entry = p["prices"].get(key)
            if not entry or entry.get("from") is None:
                continue
            if p["model"] == "consult_only":
                continue  # pharmacy prices are not comparable to subscriptions
            if best is None or entry["from"] < best[1]:
                best = (p["slug"], entry["from"])
        cheapest[key] = best
    for p in providers:
        nums = [e["from"] for e in p["prices"].values() if e.get("from") is not None]
        p["anchor_price"] = min(nums) if nums else None
        fin = p["prices"].get("oral_finasteride", {}).get("from")
        p["sort_key"] = (p["model"] == "consult_only", fin is None, fin if fin is not None else 0, p["name"].lower())
        p["is_cheapest_for"] = [k for k, v in cheapest.items() if v and v[0] == p["slug"]]
        p["format_count"] = sum(1 for e in p["prices"].values() if e.get("from") is not None)
    providers.sort(key=lambda p: p["sort_key"])
    return cheapest


def main():
    site = load_json("site.json")
    data = load_json("providers.json")
    changelog = load_json("changelog.json")
    cheapest = build_index(data)
    formats = data["formats"]
    providers = data["providers"]
    by_slug = {p["slug"]: p for p in providers}
    checked = data["checked_at"]

    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))
    env.filters["money"] = money
    env.filters["nice_date"] = nice_date
    env.globals.update(site=site, formats=formats, providers=providers, cheapest=cheapest,
                       by_slug=by_slug, checked=checked, STATUS_LABEL=STATUS_LABEL,
                       US_STATES=US_STATES, today=date.today().isoformat())

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    pages = []  # (path, priority) for the sitemap

    def render(template, out_path, **ctx):
        """out_path is site-relative, e.g. 'reviews/hims/' -> dist/reviews/hims/index.html"""
        out_dir = out_path.strip("/")
        target = DIST / out_dir / "index.html" if out_dir else DIST / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        cur = out_dir

        def rel(path):
            path = path.strip("/")
            if path.endswith(".xml") or path.endswith(".txt"):
                r = posixpath.relpath(path, cur or ".")
            else:
                r = posixpath.relpath(path or ".", cur or ".")
                if r == ".":
                    r = "./"
                elif not r.endswith("/"):
                    r += "/"
            return r

        canonical = site["base_url"].rstrip("/") + "/" + (out_dir + "/" if out_dir else "")
        html = env.get_template(template).render(rel=rel, canonical=canonical, path=out_dir, **ctx)
        target.write_text(html, encoding="utf-8")
        pages.append(out_dir)

    # Home
    render("home.html", "", title=site["name"], description=f"{site['tagline']}. {len(providers)} providers, {len(formats)} treatment formats, prices checked {nice_date(checked)}.")

    # Provider reviews
    for p in providers:
        others = [q for q in providers if q["slug"] != p["slug"]]
        render("review.html", f"reviews/{p['slug']}/", p=p, others=others,
               title=f"{p['name']} hair loss prices ({nice_date(checked)})",
               description=f"{p['name']}: every treatment format with its monthly price, fees, billing terms, cancellation policy and what to watch out for.")
    render("reviews_index.html", "reviews/", title="All provider reviews", description="Every hair-loss telehealth provider in the index, with prices and terms.")

    # Head-to-head comparisons
    pairs = []
    for a, b in combinations(providers, 2):
        a, b = sorted([a, b], key=lambda x: x["slug"])
        slug = f"{a['slug']}-vs-{b['slug']}"
        pairs.append((slug, a, b))
        render("compare.html", f"compare/{slug}/", a=a, b=b,
               title=f"{a['name']} vs {b['name']}: hair loss prices compared",
               description=f"{a['name']} and {b['name']} side by side: price per treatment format, fees, billing, cancellation and state coverage.")
    render("compare_index.html", "compare/", pairs=pairs, title="Compare any two providers", description="Head-to-head price comparisons for every pair of hair-loss telehealth providers.")

    # Cheapest by format
    for fmt in formats:
        rows = []
        for p in providers:
            e = p["prices"].get(fmt["key"])
            if e and e.get("from") is not None:
                rows.append((p, e))
        rows.sort(key=lambda r: (r[0]["model"] == "consult_only", r[1]["from"]))
        offered_unpriced = [(p, p["prices"][fmt["key"]]) for p in providers
                            if p["prices"].get(fmt["key"]) and p["prices"][fmt["key"]].get("from") is None]
        render("cheapest.html", f"cheapest/{fmt['key'].replace('_', '-')}/", fmt=fmt, rows=rows, unpriced=offered_unpriced,
               title=f"Cheapest {fmt['label'].lower()} online ({nice_date(checked)})",
               description=f"Every provider's {fmt['label'].lower()} price, lowest first, with billing terms and the catch behind each headline number.")
    render("cheapest_index.html", "cheapest/", title="Cheapest by treatment", description="Lowest verified-so-far monthly price for each hair-loss treatment format.")

    # Women
    women = [p for p in providers if p["serves"] in ("women", "both")]
    render("women.html", "women/", women=women, title="Hair loss treatment for women online: prices compared",
           description="Providers that prescribe spironolactone, oral minoxidil and topical treatments to women, with monthly prices.")

    # Cancel pages
    for p in providers:
        alts = [q for q in providers if q["slug"] != p["slug"] and q["serves"] in (p["serves"], "both") and q["anchor_price"] is not None]
        alts.sort(key=lambda q: q["anchor_price"])
        render("cancel.html", f"cancel/{p['slug']}/", p=p, alts=alts[:4],
               title=f"How to cancel {p['name']} (and what you'll pay elsewhere)",
               description=f"{p['name']}'s cancellation and refund terms as published, plus the cheapest alternatives for the same treatments.")

    # States
    render("states.html", "states/", title="Which hair loss providers ship to your state",
           description="Published state exclusions for every provider in the index.")

    # Content pages
    for slug, ttl, desc in [
        ("methodology", "How this index is built", "Where every number comes from, how providers are ordered, and what affiliate links do and do not change."),
        ("affiliate-disclosure", "Affiliate disclosure", "How the site is funded and what that changes."),
        ("about", "About", "Who runs the index and why."),
        ("privacy", "Privacy", "What this site collects."),
    ]:
        body = (CONTENT / f"{slug}.html").read_text(encoding="utf-8")
        render("page.html", f"{slug}/", body=body, title=ttl, description=desc)

    # Articles: content/articles/<slug>.html, first line a comment:
    # <!-- title: ... | date: YYYY-MM-DD | description: ... -->
    articles = []
    for f in sorted((CONTENT / "articles").glob("*.html")):
        text = f.read_text(encoding="utf-8")
        head, _, body = text.partition("-->")
        meta = {}
        for part in head.replace("<!--", "").split("|"):
            if ":" in part:
                k, v = part.split(":", 1)
                meta[k.strip()] = v.strip()
        articles.append({"slug": f.stem, "title": meta.get("title", f.stem), "date": meta.get("date", checked),
                         "description": meta.get("description", ""), "body": body.strip()})
    articles.sort(key=lambda a: a["date"], reverse=True)
    for a in articles:
        render("article.html", f"blog/{a['slug']}/", a=a, title=a["title"], description=a["description"])
    if articles:
        render("blog_index.html", "blog/", articles=articles, title="Articles", description="Guides and price notes from the index.")

    render("changelog.html", "changelog/", entries=sorted(changelog, key=lambda e: e["date"], reverse=True),
           title="Changelog", description="Every price re-check, provider addition and methodology change, newest first.")

    # 404, robots, sitemap
    render("404.html", "404-page/", title="Page not found", description="")
    shutil.move(DIST / "404-page" / "index.html", DIST / "404.html")
    (DIST / "404-page").rmdir()
    pages.remove("404-page")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site['base_url'].rstrip('/')}/sitemap.xml\n")
    base = site["base_url"].rstrip("/")
    urls = "".join(f"  <url><loc>{base}/{(p + '/') if p else ''}</loc><lastmod>{checked}</lastmod></url>\n" for p in pages)
    (DIST / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
    (DIST / ".nojekyll").write_text("")
    print(f"Built {len(pages)} pages into {DIST}")


if __name__ == "__main__":
    main()
