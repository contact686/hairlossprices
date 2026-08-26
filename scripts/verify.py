#!/usr/bin/env python3
"""Monthly price re-check.

For every provider price that has a source page, fetch the page and look for
the price on file. Results go to data/verification-log.json and any miss is
logged to data/changelog.json for a manual re-check. Nothing is ever changed
silently: a price that can't be found keeps its old value but gets flagged.

    python scripts/verify.py
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = {"User-Agent": "Mozilla/5.0 (compatible; HairLossPriceIndex/1.0; +monthly price check)"}


def fetch(url):
    try:
        r = requests.get(url, headers=UA, timeout=25)
        return r.status_code, r.text
    except requests.RequestException as e:  # noqa: BLE001
        return None, str(e)


def main():
    providers = json.loads((DATA / "providers.json").read_text(encoding="utf-8"))
    changelog = json.loads((DATA / "changelog.json").read_text(encoding="utf-8"))
    today = date.today().isoformat()
    log = {"run": today, "results": []}
    misses = []

    for p in providers["providers"]:
        pages = {}
        for url in p.get("sources", [])[:2]:  # the first two sources are the provider's own pages when available
            if p["url"].split("/")[2].replace("www.", "") in url:
                status, text = fetch(url)
                pages[url] = (status, text)
        if not pages:
            status, text = fetch(p["url"])
            pages[p["url"]] = (status, text)

        for key, entry in p["prices"].items():
            price = entry.get("from")
            if price is None:
                continue
            found_on = None
            fetched_ok = False
            for url, (status, text) in pages.items():
                if status == 200:
                    fetched_ok = True
                    if re.search(r"\$\s?%d(?![\d])" % int(price), text):
                        found_on = url
                        break
            result = {"provider": p["slug"], "format": key, "price": price,
                      "found": found_on is not None, "fetched": fetched_ok, "url": found_on or list(pages)[0]}
            log["results"].append(result)
            if not fetched_ok:
                misses.append(f"{p['name']} {key}: source page could not be fetched")
            elif not found_on:
                misses.append(f"{p['name']} {key}: ${price} not found on the page")

    (DATA / "verification-log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    if misses:
        changelog.append({
            "date": today,
            "type": "Monthly check",
            "title": f"{len(misses)} price(s) need a manual re-check",
            "body": "; ".join(misses),
        })
    else:
        changelog.append({"date": today, "type": "Monthly check",
                          "title": "All prices on file were found on their source pages", "body": ""})
    (DATA / "changelog.json").write_text(json.dumps(changelog, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"checked {len(log['results'])} prices, {len(misses)} to re-check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
