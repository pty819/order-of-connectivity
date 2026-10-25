#!/usr/bin/env python3
"""Check chapter-two assembly and its declared snapshot; no quality certification."""
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with (ROOT / path).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def body(text):
    return re.sub(r'^\[\^R\d{4}\]:.*$', '', text, flags=re.M).strip()


def main():
    topics = rows('research/chapter-02-subtopics.csv')
    reviews = rows('research/chapter-02-sociology-review.csv')
    refs = {r['id']: r for r in rows('references/references.csv')}
    assert len(topics) == len(reviews) == 81
    assert {r['id'] for r in topics} == {r['id'] for r in reviews}
    fields = ('question', 'concept_and_scope', 'mechanism', 'evidence_read',
              'alternative_and_test', 'bounded_judgment', 'revision')
    for review in reviews:
        assert review['review_status'] == 'reviewed' and all(review[f].strip() for f in fields)
    chapter = ROOT / 'book/chapters/02-restructuring'
    reader = (chapter / 'manuscript.md').read_text()
    frame = (chapter / 'chapter-frame.md').read_text()
    assert len(re.findall(r'^## 2\.\d+　', reader, re.M)) == 17
    assert len(re.findall(r'^### 2\.\d+\.\d+　', reader, re.M)) == 81
    start, end = body(frame).split('<!-- CHAPTER BODY -->')
    assert start.split('\n', 1)[1].strip() in reader and end.strip() in reader
    for row in topics:
        text = (ROOT / row['manuscript']).read_text()
        assert text.splitlines()[0] == '# ' + row['title']
        passage = body(text).split('\n', 1)[1].lstrip()
        passage = re.sub(r'\A第二章·2\.\d+\.\d+。', '', passage)
        passage = re.sub(r'^(#{2,}) ', lambda m: '##' + m[1] + ' ', passage, flags=re.M)
        assert passage in reader, row['id']
        uses = set(re.findall(r'\[\^(R\d{4})\](?!:)', text))
        assert uses == set(row['source_ids'].split(';')), row['id']
        for rid, url in re.findall(r'^\[\^(R\d{4})\]:.*?\]\((https?://[^\s)]+)\)', text, re.M):
            assert refs[rid]['url'] == url, (row['id'], rid)
    uses = set(re.findall(r'\[\^(R\d{4})\](?!:)', reader))
    definitions = re.findall(r'^\[\^(R\d{4})\]:', reader, re.M)
    assert len(definitions) == len(set(definitions)) and set(definitions) == uses
    assert not any(refs[r]['verification'] in {
        'pending_read', 'unavailable', 'abstract_metadata', 'publisher_catalogue'} for r in uses)
    unresolved = [r['id'] for r in rows('research/claims.csv')
                  if '/02-restructuring/' in r['manuscript'] and r['classification'] == 'unresolved']
    assert unresolved == ['C0763', 'C0848', 'C0884']
    baseline = '0b745c9828dd105c39507f34870bbefc967a2957'
    assert not subprocess.check_output(
        ['git', 'diff', baseline, '--', 'book/chapters/01-scarcity'], cwd=ROOT)
    snapshot = json.loads((ROOT / 'research/chapter-02-sociology-integrity.json').read_text())
    for path, expected in snapshot['sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    assert snapshot['topics_reviewed'] == 81 and snapshot['topics_pending'] == 0
    print(f'PASS: 81 sociology records, 81 complete bodies, 17 sections, {len(uses)} cited sources;')
    print('full frame, source bindings, snapshot hashes, three unresolved items and unchanged chapter one.')
    print('This checks traceability and assembly, not the truth or sufficiency of historical arguments.')


if __name__ == '__main__':
    main()
