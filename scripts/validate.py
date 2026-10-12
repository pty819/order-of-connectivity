#!/usr/bin/env python3
"""Validate editorial links and citation relationships, not historical truth."""
import csv
import json
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
    if u.scheme not in {"https", "http"} or not u.netloc or u.username or u.password:
        errors.append(f"{r['id']}: invalid public HTTP(S) source URL")
    if u.scheme == "http" and "HTTP原站" not in r.get('notes', ''):
        errors.append(f"{r['id']}: legacy HTTP source requires its retrieval boundary recorded")
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
extra_documents = [p for p in [outline_document, ROOT / 'research/outline-expansion-v2.md', ROOT / 'research/outline-expansion-v3.md'] if p.exists()]
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
section_rows = table('research/section-outline-v1.csv', [
    'id', 'chapter_id', 'section_order', 'title', 'question', 'subtopics', 'narrative',
    'source_ids', 'evidence_needed', 'cross_refs', 'status',
])
section_document = ROOT / 'book/SECTION_OUTLINE.md'
section_text = section_document.read_text(encoding='utf-8')
section_lookup = {r['id']: r for r in section_rows}
ref_lookup = {r['id']: r for r in refs}
for c in chapter_rows:
    group = [r for r in section_rows if r['chapter_id'] == c['id']]
    orders = [int(r['section_order']) for r in group]
    if not group or orders != list(range(1, len(group) + 1)):
        errors.append(f"{c['id']}: section numbering must be nonempty, ordered and continuous")
    if any(not re.fullmatch(c['id'] + r'-S\d{2}', r['id']) for r in group):
        errors.append(f"{c['id']}: invalid permanent section ID")
    expected_titles = ';'.join(
        f"{int(c['id'][2:])}.{i} {r['title']}" for i, r in enumerate(group, 1)
    )
    if c['sections'] != expected_titles:
        errors.append(f"{c['id']}: chapter sections drifted from detailed section table")
for r in section_rows:
    if r['chapter_id'] not in chapter_ids:
        errors.append(f"{r['id']}: unknown parent chapter")
    if any(not r[f] for f in r if f not in {'source_ids', 'cross_refs'}):
        errors.append(f"{r['id']}: missing section writing field")
    if len(r['subtopics'].split(';')) < 3 or any(not t for t in r['subtopics'].split(';')):
        errors.append(f"{r['id']}: expected at least three nonempty internal topics")
    try:
        notes = json.loads(r.get('subtopic_notes') or '{}')
        valid_positions = {str(i) for i in range(1, len(r['subtopics'].split(';')) + 1)}
        if not isinstance(notes, dict) or set(notes) - valid_positions or any(not isinstance(v, str) or not v.strip() for v in notes.values()):
            errors.append(f"{r['id']}: invalid subtopic writing notes")
    except json.JSONDecodeError:
        errors.append(f"{r['id']}: malformed subtopic writing notes")
    expected_status = 'existing_entry' if r['source_ids'] else 'planned_research'
    if r['status'] != expected_status:
        errors.append(f"{r['id']}: status must distinguish finite source entry from planned research")
    for field in ('source_ids', 'cross_refs'):
        values = list(filter(None, r[field].split(';')))
        if len(values) != len(set(values)):
            errors.append(f"{r['id']}: duplicate {field}")
    for source in filter(None, r['source_ids'].split(';')):
        if source not in ref_lookup or ref_lookup[source]['verification'] in {'pending_read', 'unavailable'}:
            errors.append(f"{r['id']}: unread or unregistered source entry {source}")
    for target in filter(None, r['cross_refs'].split(';')):
        if target not in section_lookup or section_lookup[target]['id'] == r['id']:
            errors.append(f"{r['id']}: broken or self-referencing section target {target}")
    anchor = f'<a id="{r["id"].lower()}"></a>'
    if anchor not in section_text or f"SECTION_OUTLINE.md#{r['id'].lower()}" not in summary_text:
        errors.append(f"{r['id']}: detailed section missing from generated document/index")
    if re.fullmatch(r'CH\d{2}-S\d{2}', r['id']):
        number = f"{int(r['chapter_id'][2:])}.{int(r['section_order'])}"
        if f"### {number}　{r['title']}" not in section_text:
            errors.append(f"{r['id']}: rendered section title drifted")
expansion_rows = table('research/outline-expansion-v2.csv', [
    'id', 'section_id', 'change_type', 'source_ids', 'gap_identified', 'added_scope', 'reading_boundary',
])
expansion_rows += table('research/outline-expansion-v3.csv', [
    'id', 'section_id', 'change_type', 'source_ids', 'gap_identified', 'added_scope', 'reading_boundary',
])
expansion_text = '\n'.join((ROOT / f'research/outline-expansion-{version}.md').read_text(encoding='utf-8') for version in ['v2', 'v3'])
for r in expansion_rows:
    if any(not r[f] for f in r) or r['change_type'] not in {'new_section', 'deepened_section'}:
        errors.append(f"{r['id']}: incomplete or invalid literature expansion record")
    section = section_lookup.get(r['section_id'])
    if not section:
        errors.append(f"{r['id']}: unknown expansion section")
        continue
    if set(r['source_ids'].split(';')) - set(section['source_ids'].split(';')):
        errors.append(f"{r['id']}: expansion source missing from section")
    if f"SECTION_OUTLINE.md#{r['section_id'].lower()}" not in expansion_text:
        errors.append(f"{r['id']}: expansion missing from readable report")
chapter_one_path = ROOT / 'research/chapter-01-subtopics.csv'
chapter_one_rows = table('research/chapter-01-subtopics.csv', [
    'id', 'section_id', 'subtopic_order', 'title', 'manuscript', 'status', 'source_ids', 'review_note',
]) if chapter_one_path.exists() else []
if chapter_one_rows:
    expected = {
        f"{s['id']}-T{i:02d}": (s['id'], str(i), title)
        for s in section_rows if s['chapter_id'] == 'CH01'
        for i, title in enumerate(s['subtopics'].split(';'), 1)
    }
    if {r['id'] for r in chapter_one_rows} != set(expected):
        errors.append('chapter one: manuscript scope must preserve every outlined internal topic')
    for r in chapter_one_rows:
        if (r['section_id'], r['subtopic_order'], r['title']) != expected.get(r['id']):
            errors.append(f"{r['id']}: chapter-one topic mapping drifted")
        if not r['review_note'] or r['status'] not in {'planned', 'research_draft', 'revised_draft'}:
            errors.append(f"{r['id']}: invalid manuscript status or missing review boundary")
        path = ROOT / r['manuscript']
        if r['status'] != 'planned':
            if not path.is_file():
                errors.append(f"{r['id']}: manuscript status claims absent file")
                continue
            if path.read_text(encoding='utf-8').splitlines()[0] != '# ' + r['title']:
                errors.append(f"{r['id']}: manuscript title mismatch")
            if not r['source_ids'] or set(r['source_ids'].split(';')) - ref_ids:
                errors.append(f"{r['id']}: missing or unregistered manuscript source IDs")
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
print(f"PASS: {len(topics)} topics, {len(refs)} source records, {len(used)} cited sources, {len(claims)} claims, {len(drafts)} legacy topic drafts, {characters} Chinese characters in those drafts")
if data_rows:
    print(f"Cost table: {len(data_rows)} transcribed rows; totals and rounded percentages agree.")
if scenario_rows:
    print(f"Income scenario: {len(scenario_rows)} source values and hypothetical-price ratios agree; not an affordability estimate.")
if outline_rows:
    print(f"Source outline: {len(outline_rows)} topic scopes, manuscript links, read-evidence IDs and remaining questions present; not a completion claim for the book.")
print(f"Chapter plan: {len(chapter_rows)} chapters, all 17 topics and all existing drafts mapped; chapter writing remains incomplete.")
print(f"Section outline: {len(section_rows)} sections, {sum(len(r['subtopics'].split(';')) for r in section_rows)} internal topics; numbering, cross-references, source states and generated index agree.")
print(f"Literature expansion: {sum(r['change_type'] == 'new_section' for r in expansion_rows)} new sections, {sum(r['change_type'] == 'deepened_section' for r in expansion_rows)} deepened sections with traceable sources and reading boundaries.")
if chapter_one_rows:
    written = sum(r['status'] != 'planned' for r in chapter_one_rows)
    print(f"Chapter one manuscripts: {written}/{len(chapter_one_rows)} research drafts present; {len(chapter_one_rows)-written} topics still planned. Structural check is not editorial or historical review.")
print("Scope: references, CSV relationships and local links only; no assertion of historical accuracy or book completion.")
