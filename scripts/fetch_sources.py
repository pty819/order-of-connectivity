#!/usr/bin/env python3
"""Fetch public sources to ignored local cache; success is not claim verification."""
import argparse
import concurrent.futures
import csv
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def fetch(row):
    result = {"id": row["id"], "requested_url": row["url"]}
    try:
        req = urllib.request.Request(row["url"], headers={"User-Agent": "Mozilla/5.0 (historical research)"})
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            result.update(status=response.status, final_url=response.url,
                          content_type=response.headers.get("Content-Type", ""),
                          sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        suffix = ".pdf" if raw.startswith(b"%PDF") else ".html"
        (ROOT / ".research-cache" / (row["id"] + suffix)).write_bytes(raw)
    except Exception as exc:
        result["error"] = str(exc)
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("ids", nargs="*")
    args = p.parse_args()
    rows = list(csv.DictReader((ROOT / "references/references.csv").open(encoding="utf-8", newline="")))
    if args.ids:
        rows = [r for r in rows if r["id"] in args.ids]
    (ROOT / ".research-cache").mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(fetch, rows))
    out = ROOT / ".research-cache/fetch-results.json"
    old = json.loads(out.read_text()) if out.exists() else []
    merged = {r["id"]: r for r in old}
    merged.update({r["id"]: r for r in results})
    out.write_text(json.dumps(list(merged.values()), ensure_ascii=False, indent=2) + "\n")
    for r in results:
        print(r["id"], r.get("status", r.get("error")), r.get("bytes", ""))

if __name__ == "__main__":
    main()
