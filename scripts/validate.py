#!/usr/bin/env python3
"""Validate editorial links and citation relationships, not historical truth."""
import csv
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
errors = []

def table(path, required):
    with (ROOT / path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(required) - set(reader.fieldnames or [])
        if missing:
            errors.append(f"{path}: missing columns {sorted(missing)}")
        rows = list(reader)
    ids = [r.get("id") for r in rows]
    if len(ids) != len(set(ids)) or not all(ids):
        errors.append(f"{path}: empty or duplicate IDs")
    if any(None in r for r in rows):
        errors.append(f"{path}: malformed CSV row")
    return rows

refs = table("references/references.csv", ["id", "title", "creator", "url", "verification", "locator", "accessed_at"])
ref_ids = {r["id"] for r in refs}
allowed = {"full_text", "partial_text", "abstract_metadata", "publisher_catalogue", "indexed_excerpt", "indexed_full_text", "pending_read", "unavailable"}
for r in refs:
    u = urlsplit(r["url"])
    if u.scheme != "https" or not u.netloc or u.username or u.password:
        errors.append(f"{r['id']}: invalid public HTTPS URL")
    if r["verification"] not in allowed:
        errors.append(f"{r['id']}: unknown verification status")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["accessed_at"]):
        errors.append(f"{r['id']}: missing access/attempt date")

topics = table("research/topics.csv", ["id", "discussion_order", "topic", "chapter", "status"])
if sorted(int(r["discussion_order"]) for r in topics) != list(range(1, 18)):
    errors.append("topics.csv: original discussion requires all 17 topics exactly once")

used = set()
book_files = list((ROOT / "book").rglob("*.md"))
for path in [ROOT / "README.md", ROOT / "CONTRIBUTING.md"] + book_files:
    text = path.read_text(encoding="utf-8")
    prose = re.sub(r"```[\s\S]*?```", "", text)
    prose = re.sub(r"`[^`\n]*`", "", prose)
    cited = set(re.findall(r"\[\^(R\d{4})\](?!:)", prose))
    defined = set(re.findall(r"^\[\^(R\d{4})\]:", text, re.M))
    if cited != defined:
        errors.append(f"{path.relative_to(ROOT)}: citation/definition mismatch {sorted(cited ^ defined)}")
    if cited - ref_ids:
        errors.append(f"{path.relative_to(ROOT)}: unregistered references {sorted(cited - ref_ids)}")
    used |= cited
    for target in re.findall(r"\]\(([^\s)]+)\)", text):
        u = urlsplit(target)
        if not u.scheme and u.path:
            local = (path.parent / unquote(u.path)).resolve()
            if not local.exists():
                errors.append(f"{path.relative_to(ROOT)}: broken local link {target}")
    if re.search(r"turn\d+(search|view|fetch)\d+", text):
        errors.append(f"{path.relative_to(ROOT)}: internal browser citation leaked")

claims = table("research/claims.csv", ["id", "topic_id", "claim", "classification", "source_ids", "locator", "limitation", "manuscript"])
topic_ids = {r["id"] for r in topics}
for r in claims:
    if r["topic_id"] not in topic_ids:
        errors.append(f"{r['id']}: unknown topic")
    if set(filter(None, r["source_ids"].split(";"))) - ref_ids:
        errors.append(f"{r['id']}: unknown source")
    if r["classification"] not in {"documented", "corroborated", "interpretation", "unresolved"}:
        errors.append(f"{r['id']}: unknown claim category")
    if not (ROOT / r["manuscript"]).exists():
        errors.append(f"{r['id']}: missing manuscript")
    if not r["limitation"]:
        errors.append(f"{r['id']}: evidence boundary not recorded")

if errors:
    print("\n".join(errors))
    sys.exit(1)
drafts = [p for p in book_files if "/topics/" in str(p)]
characters = sum(len(re.findall(r"[\u4e00-\u9fff]", p.read_text(encoding="utf-8"))) for p in drafts)
print(f"PASS: {len(topics)} topics, {len(refs)} source records, {len(used)} cited sources, {len(claims)} claims, {len(drafts)} drafts, {characters} Chinese characters")
print("Scope: references, CSV relationships and local links only; no assertion of historical accuracy or book completion.")
