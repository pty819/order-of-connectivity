#!/usr/bin/env python3
"""Validate editorial links and citation relationships, not historical truth."""
import csv
from decimal import Decimal, ROUND_HALF_UP
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
outline_document = ROOT / "research/source-outline-v1.md"
extra_documents = [outline_document] if outline_document.exists() else []
for path in [ROOT / "README.md", ROOT / "CONTRIBUTING.md"] + book_files + extra_documents:
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
for r in refs:
    if r["id"] in used and r["verification"] in {"pending_read", "unavailable"}:
        errors.append(f"{r['id']}: manuscript cites a source that has not been read")
topic_ids = {r["id"] for r in topics}
chapter_rows = table("research/chapter-plan-v1.csv", [
    "id", "title", "period", "topic_ids", "support_topic_ids", "question", "opening",
    "sections", "narrative", "remaining_work", "boundary", "manuscripts", "source_ids", "status",
])
chapter_ids = {r['id'] for r in chapter_rows}
if [r['id'] for r in chapter_rows] != [f'CH{i:02d}' for i in range(1, 11)]:
    errors.append("chapter plan: expected ten ordered chapters CH01 through CH10")
covered_topics, covered_manuscripts = set(), set()
plan_text = (ROOT / 'book/CHAPTER_PLAN.md').read_text(encoding='utf-8')
summary_text = (ROOT / 'book/SUMMARY.md').read_text(encoding='utf-8')
for number, r in enumerate(chapter_rows, 1):
    if any(not r[field] for field in r if field != 'support_topic_ids') or r['status'] != 'plan_v1':
        errors.append(f"{r['id']}: incomplete chapter plan or wrong status")
    linked_topics = set(filter(None, (r['topic_ids'] + ';' + r['support_topic_ids']).split(';')))
    covered_topics |= linked_topics
    if linked_topics - topic_ids:
        errors.append(f"{r['id']}: unknown topic")
    for source in r['source_ids'].split(';'):
        if source not in ref_ids:
            errors.append(f"{r['id']}: unregistered source {source}")
    for manuscript in r['manuscripts'].split(';'):
        covered_manuscripts.add(manuscript)
        if not (ROOT / manuscript).is_file():
            errors.append(f"{r['id']}: missing manuscript {manuscript}")
    if f'<a id="{r["id"].lower()}"></a>' not in plan_text:
        errors.append(f"{r['id']}: missing chapter anchor")
    if f"## 第{number}章：{r['title']}" not in summary_text:
        errors.append(f"{r['id']}: reading index title mismatch")
if covered_topics != topic_ids:
    errors.append("chapter plan: must retain all 17 discussion topics, including editorial support")
draft_paths = {str(p.relative_to(ROOT)) for p in book_files if '/topics/' in str(p)}
if not draft_paths <= covered_manuscripts:
    errors.append(f"chapter plan: unmapped drafts {sorted(draft_paths - covered_manuscripts)}")
for r in topics:
    positions = set(r['chapter'].split(';'))
    if positions - chapter_ids - {'introduction'}:
        errors.append(f"{r['id']}: unknown chapter position")
    for position in positions & chapter_ids:
        chapter = next(c for c in chapter_rows if c['id'] == position)
        if r['id'] not in chapter['topic_ids'].split(';'):
            errors.append(f"{r['id']}: chapter/topic mapping mismatch")
outline_path = ROOT / "research/source-outline-v1.csv"
outline_rows = table("research/source-outline-v1.csv", [
    "id", "period", "subtopics", "manuscripts", "source_ids", "outline_status",
    "evidence_summary", "narrative", "remaining_work",
]) if outline_path.exists() else []
if outline_rows:
    if {r['id'] for r in outline_rows} != topic_ids:
        errors.append("source outline: must preserve all 17 discussion topics")
    ref_lookup = {r['id']: r for r in refs}
    outline_text = outline_document.read_text(encoding='utf-8') if outline_document.exists() else ''
    for r in outline_rows:
        if any(not r[field] for field in r):
            errors.append(f"{r['id']}: incomplete source-outline fields")
        if r['outline_status'] != 'outline_v1' or f"## {r['id']}" not in outline_text:
            errors.append(f"{r['id']}: source-outline section/status missing")
        for source in r['source_ids'].split(';'):
            if source not in ref_lookup or ref_lookup[source]['verification'] in {'pending_read', 'unavailable'}:
                errors.append(f"{r['id']}: unread or unregistered outline evidence {source}")
        for manuscript in r['manuscripts'].split(';'):
            if not (ROOT / manuscript).is_file():
                errors.append(f"{r['id']}: missing outline manuscript {manuscript}")
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

# Only the explicitly transcribed cost table is covered by this arithmetic check.
data_path = ROOT / "research/data/greatwall-costs-2010-2012.csv"
data_rows = list(csv.DictReader(data_path.open(encoding="utf-8", newline=""))) if data_path.exists() else []
if data_rows:
    if len(data_rows) != 24 or len({(r['period'], r['category']) for r in data_rows}) != 24:
        errors.append("cost table: expected 24 distinct period/category rows")
    for period in {r['period'] for r in data_rows}:
        group = [r for r in data_rows if r['period'] == period]
        total_rows = [r for r in group if r['category'] == '合计']
        if len(total_rows) != 1:
            errors.append(f"cost table {period}: missing/duplicate total")
            continue
        total = Decimal(total_rows[0]['cost'])
        parts = [r for r in group if r['category'] != '合计']
        if sum(Decimal(r['cost']) for r in parts) != total:
            errors.append(f"cost table {period}: amounts do not sum")
        for r in group:
            if r['source_id'] not in ref_ids or r['unit'] != '万元人民币':
                errors.append(f"cost table {period}: source/unit mismatch")
            if abs(Decimal(r['cost']) / total * 100 - Decimal(r['share_percent'])) > Decimal('.02'):
                errors.append(f"cost table {period}: percentage mismatch")

scenario_path = ROOT / "research/data/device-price-income-2025.csv"
scenario_rows = list(csv.DictReader(scenario_path.open(encoding="utf-8", newline=""))) if scenario_path.exists() else []
if scenario_rows:
    source_values = {
        "低收入组": "10150", "中间偏下收入组": "22702", "中间收入组": "35536",
        "中间偏上收入组": "55586", "高收入组": "103778",
    }
    if len(scenario_rows) != 5 or {r['income_group'] for r in scenario_rows} != set(source_values):
        errors.append("income scenario: expected five distinct income groups")
    for r in scenario_rows:
        if (r['annual_per_capita_disposable_income'] != source_values.get(r['income_group'])
                or r['year'] != '2025' or r['currency'] != 'CNY' or r['source_id'] != 'R0122'
                or r['hypothetical_device_price'] != '3000' or not r['scenario_note']):
            errors.append("income scenario: source value, unit or explicit assumption mismatch")
        expected = (Decimal(r['hypothetical_device_price']) / Decimal(r['annual_per_capita_disposable_income'])
                    * 100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        if Decimal(r['price_income_percent']) != expected:
            errors.append("income scenario: price-income percentage mismatch")

if errors:
    print("\n".join(errors))
    sys.exit(1)
drafts = [p for p in book_files if "/topics/" in str(p)]
characters = sum(len(re.findall(r"[\u4e00-\u9fff]", p.read_text(encoding="utf-8"))) for p in drafts)
print(f"PASS: {len(topics)} topics, {len(refs)} source records, {len(used)} cited sources, {len(claims)} claims, {len(drafts)} drafts, {characters} Chinese characters")
if data_rows:
    print(f"Cost table: {len(data_rows)} transcribed rows; totals and rounded percentages agree.")
if scenario_rows:
    print(f"Income scenario: {len(scenario_rows)} source values and hypothetical-price ratios agree; not an affordability estimate.")
if outline_rows:
    print(f"Source outline: {len(outline_rows)} topic scopes, manuscript links, read-evidence IDs and remaining questions present; not a completion claim for the book.")
print(f"Chapter plan: {len(chapter_rows)} chapters, all 17 topics and all existing drafts mapped; chapter writing remains incomplete.")
print("Scope: references, CSV relationships and local links only; no assertion of historical accuracy or book completion.")
