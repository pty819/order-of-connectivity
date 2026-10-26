#!/usr/bin/env python3
"""Render chapter plans, detailed section outlines and the reading index."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_table(path):
    with (ROOT / path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def section_number(row):
    return f"{int(row['chapter_id'][2:])}.{int(row['section_order'])}"


def manuscript_title(path):
    for line in (ROOT / path).read_text(encoding='utf-8').splitlines():
        if line.startswith('# '):
            return line[2:].strip()
    raise ValueError(f'No manuscript title: {path}')


def render_chapter_one(sections):
    path = ROOT / 'research/chapter-01-subtopics.csv'
    if not path.exists():
        return
    topics = read_table('research/chapter-01-subtopics.csv')
    completed = sum(r['status'] != 'planned' for r in topics)
    remaining = len(topics) - completed
    rewritten = sum(r['status'] == 'revised_draft' for r in topics)
    editorial_file = ROOT / 'research/chapter-01-editorial-status.json'
    editorial = json.loads(editorial_file.read_text(encoding='utf-8')) if editorial_file.exists() else {}
    reviewed = editorial.get('argument_revision') == 'complete'
    progress = f'另有{remaining}项待写' if remaining else '材料底稿覆盖全部话题'
    if reviewed:
        revision = '75篇已完成本轮论述改写、逐篇审读及整章整合（2026-10-23）；仍为保留证据边界的研究初稿。'
    elif rewritten == len(topics):
        revision = '75篇已覆盖首轮论述改写；全章正在审读，深度、衔接与删重尚未完成。'
    else:
        revision = f'其中{rewritten}篇完成本轮论述重写，{completed-rewritten}篇仍待重写；全章尚未完成论述修订。'
    lines = ['', f'话题文件：{completed}/{len(topics)}；{progress}。{revision}', '']
    for section in sections:
        if section['chapter_id'] != 'CH01':
            continue
        number = section_number(section)
        lines.extend([f"## {number}　{section['title']}", ''])
        for r in topics:
            if r['section_id'] != section['id']:
                continue
            label = f"{number}.{r['subtopic_order']}　{r['title']}"
            if r['status'] == 'planned':
                lines.append(f'- {label}（待写）')
            else:
                stage = '论述修订稿，已内部审读' if reviewed else ('论述重写稿' if r['status'] == 'revised_draft' else '史料型底稿，待论述重写')
                lines.append(f"- [{label}](subtopics/{Path(r['manuscript']).name})（{stage}）")
        lines.append('')
    doc = ROOT / 'book/chapters/01-scarcity/README.md'
    current = doc.read_text(encoding='utf-8')
    start = '<!-- BEGIN CH01 INDEX -->'
    end = '<!-- END CH01 INDEX -->'
    prefix, tail = current.split(start, 1)
    _, suffix = tail.split(end, 1)
    doc.write_text(prefix + start + '\n' + '\n'.join(lines) + '\n' + end + suffix, encoding='utf-8')


def render_expansion(sections):
    changes = read_table('research/outline-expansion-v2.csv')
    refs = {r['id']: r for r in read_table('references/references.csv')}
    section_map = {s['id']: s for s in sections}
    new_count = sum(r['change_type'] == 'new_section' for r in changes)
    deep_count = sum(r['change_type'] == 'deepened_section' for r in changes)
    lines = [
        '# 文献对照与大纲增补记录', '',
        f'版本：2026-10-12。本轮从102节继续研究，增加{new_count}节、加深{deep_count}节。文献表新增R0165—R0203共39条记录；记录包含指定节段、摘要、目录与公开书摘，不能一概称为全文阅读。', '',
        '本记录回答每项扩展由什么材料提示、原纲遗漏什么、还有什么没有核实。研究问题与主题扩展不是新的史实定论，原18篇专题正文及200条事实证据关系没有因此变成全书定稿。', '',
        '## 参与者回忆材料怎样使用', '',
        '王建宙是国企经营者，其《移动时代生存》及《从1G到5G》的书目已经核到，另读了公开转引书摘与2021访谈相关段。公开书摘尚未与原书页码对照，不能声称读完两本书。张立贵的材料是新闻对历史言论的转引，不是找到了一部完整自传。', '',
        '吴基传、刘彩属于行业主管与政策参与者；其亲历访谈用于追踪建设、财务、改革争论和实施，不能统称国企领导回忆录。《朱高峰传》由刘建辉编写，本轮只到书目、目录与前言入口；另读朱高峰采访的载波研发和筹资段，不将他人传记称为本人自述。', '',
        '回忆可提供决策者当时的认识与后来解释，需与原文件、合同、工程记录、其他参与者及用户互校。特别注意部门立场、事后成败叙事、发布日期和事件日、机构归口与年份，以及技术和数值的简化。', '',
        '## 学术文献的阅读边界', '',
        '研究补入制度与市场机制、普遍服务、制造集群、迁移劳动、性别、互联网记忆、资本与技术学习、合同研发和网络韧性。Loo、Xia、Yang/Wu、Wallis及若干产业研究的部分入口仅为摘要或目录；具体样本、案例和因果检验需要继续读全文。', '',
        'TSE取得的是2023年29页工作稿的指定段，不混用其2025修订版本及样本。国内铁塔改革研究只读到索引节段，另用作者机构页核书目，不声称核过其估计结果。Fuller取得的是合法30页预览，非整本书；会议论文只支持其都江堰案例和已读范围。', '',
        '宽带中国、IPv6、实名、携号转网、商务楼宇和适老化原规范，以及信通院蓝皮书和企业资料提供另一层对照。规定及目标不能自动证明实施，企业与研究机构自述不能单独证明绩效。', '',
        '## 来源索引', '',
    ]
    # 展示本轮入库资料，包括用于既有小节和进一步补证的入口。
    for r in refs.values():
        if 165 <= int(r['id'][1:]) <= 203:
            lines.append(f"- **{r['id']}** [{r['title']}]({r['url']})；{r['creator']}；{r['verification']}；{r['locator']}。{r['notes']}")
    for c in sorted({s['chapter_id'] for s in sections}):
        lines.extend(['', f"## 第{int(c[2:])}章的增补", ''])
        for row in changes:
            s = section_map[row['section_id']]
            if s['chapter_id'] != c:
                continue
            typ = '新增小节' if row['change_type'] == 'new_section' else '加深原节'
            lines.extend([
                f"### {typ}：[{section_number(s)}　{s['title']}](../book/SECTION_OUTLINE.md#{s['id'].lower()})", '',
                f"原纲缺口：{row['gap_identified']}", '',
                f"新增范围：{row['added_scope'].replace(';', '；')}。", '',
                f"文献依据：{'、'.join(row['source_ids'].split(';'))}。", '',
                f"仍需核验：{row['reading_boundary']}", '',
            ])
    lines.extend([
        '## 下一步补读的具体材料', '',
        '优先取得朱高峰传关于核算、干部和邮电管理的原章节，以及王建宙两书完整版本与书摘页码；补三定、财务分割、税费留用和中中外原合同；补铁塔资产、租赁和研究全文；补国内外资、社区接入、退网与用户材料；补迁移、性别、适老和疫情专题；补芯片制造、资本、合同研发和云算力的长期对照。', '',
        '本记录由[变更CSV](outline-expansion-v2.csv)生成。原小节使用永久ID，新位置由排序字段控制；显示节号可以调整，已有锚点继续定位原主题。',
    ])
    (ROOT / 'research/outline-expansion-v2.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def render_sections(chapters, sections):
    refs = {r['id']: r for r in read_table('references/references.csv')}
    lookup = {s['id']: s for s in sections}
    reading = {
        'full_text': '全文', 'partial_text': '指定节段',
        'abstract_metadata': '摘要与元数据', 'publisher_catalogue': '目录或元数据',
        'indexed_excerpt': '索引节段', 'indexed_full_text': '索引全文',
    }
    count = sum(len(s['subtopics'].split(';')) for s in sections)
    lines = [
        '# 十章详细大纲：小节与内部话题', '',
        f"版本：2026-10-12。导论之外的十章共{len(sections)}个小节、{count}个三级话题。每节规定研究问题、内部话题、叙事安排、现有史料入口、补证重点和跨节衔接，可直接用于分配资料及扩写正文。", '',
        '本文件是写作大纲。标题和研究问题不等于已核实的结论；列出的企业、案例和关系均须在正文阶段以材料检验。现有入口只承担文献表登记的阅读范围，不表示足够支持本节全部话题。没有逐项绑定入口的小节保留为研究任务。', '',
        '章级论证见[十章方案](CHAPTER_PLAN.md)，既有稿件见[阅读目录](SUMMARY.md)，原研讨范围见[17主题史料总纲](../research/source-outline-v1.md)。导论保留研究对象、方法和证据制度，不另算主体章节。', '',
        '文献扩展分轮记录：从102节到154节的[第二轮文献对照](../research/outline-expansion-v2.md)，以及从154节继续增加20节、加深20节的[第三轮扩展](../research/outline-expansion-v3.md)。本轮160个新增内部话题附有具体写作说明；节内话题数量随问题变化。', '',
        '## 章节索引', '',
        '|章|标题|小节数|', '|---|---|---|',
    ]
    for c in chapters:
        total = sum(s['chapter_id'] == c['id'] for s in sections)
        lines.append(f"|[第{int(c['id'][2:])}章](#{c['id'].lower()})|{c['title']}|{total}|")
    for c in chapters:
        n = int(c['id'][2:])
        selected = [s for s in sections if s['chapter_id'] == c['id']]
        lines.extend([
            '', f'<a id="{c["id"].lower()}"></a>', '',
            f"## 第{n}章：{c['title']}", '',
            f"时间重心：{c['period']}。", '',
            f"全章问题：{c['question']}", '',
            f"论证推进：{c['narrative']}", '',
            '本章小节：', '',
        ])
        for s in selected:
            lines.append(f"- [{section_number(s)}　{s['title']}](#{s['id'].lower()})")
        for s in selected:
            label = section_number(s)
            lines.extend([
                '', f'<a id="{s["id"].lower()}"></a>', '',
                f"### {label}　{s['title']}", '',
                f"**要回答的问题**：{s['question']}", '',
                '**内部话题**：', '',
            ])
            notes = json.loads(s.get('subtopic_notes') or '{}')
            for i, topic in enumerate(s['subtopics'].split(';'), 1):
                lines.append(f'- {label}.{i}　{topic}')
                if str(i) in notes:
                    lines.extend(['', '  ' + notes[str(i)], ''])
            lines.extend(['', f"**叙事安排**：{s['narrative']}", '', '**现有史料入口及已读范围**：', ''])
            if s['source_ids']:
                for ref_id in s['source_ids'].split(';'):
                    r = refs[ref_id]
                    lines.append(f"- {ref_id} [{r['title']}]({r['url']})；{reading[r['verification']]}；{r['locator']}。")
            else:
                lines.append('暂无逐项绑定的已读入口，先取得下列原件和对照材料。')
            lines.extend(['', f"**补证重点**：{s['evidence_needed']}"])
            if s['cross_refs']:
                targets = []
                for target_id in s['cross_refs'].split(';'):
                    target = lookup[target_id]
                    targets.append(f"[{section_number(target)}　{target['title']}](#{target['id'].lower()})")
                lines.extend(['', '**衔接与分工**：与' + '、'.join(targets) + '互相参照；同一事件以其主要小节叙述为准，本节只展开与自身问题有关的部分。'])
    lines.extend([
        '', '## 扩写和整合顺序', '',
        '先为每节整理时间线、参与者、原文件、可比指标及争议。第一章按用户要求，每个三级话题单独形成详细Markdown，再作章内衔接；其他章在正式扩写时确定文件安排。最终排版可以合并标题，但研究范围不能因排版被删。', '',
        '优先补第一、二章的工程、资费、成立及交割原件；随后补第三至六章的服务、合同、历史拓扑与标准实施；最后补第七至十章的供应链、家庭、资本和工厂对照。已有稿可先归入相应小节，完成局部核验后再做全章过渡与删重。', '',
        '每章末只总结本章可支持的判断并引出下一章，第十章末进行全书综合。跨节引用不得代替证据，研究问题不预写成结论。', '',
        '结构来源：[小节大纲CSV](../research/section-outline-v1.csv)；章级来源：[十章方案CSV](../research/chapter-plan-v1.csv)。两者由`python3 scripts/build_chapter_plan.py`统一生成阅读文件，随后运行`python3 scripts/validate.py`核对。',
    ])
    (ROOT / 'book/SECTION_OUTLINE.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return count


def render_expansion_v3(sections):
    changes = read_table('research/outline-expansion-v3.csv')
    refs = {r['id']: r for r in read_table('references/references.csv')}
    lookup = {s['id']: s for s in sections}
    changes.sort(key=lambda r: (lookup[r['section_id']]['chapter_id'], int(lookup[r['section_id']]['section_order'])))
    lines = [
        '# 第三轮大纲扩展：劳动、工程、企业与使用者', '',
        '2026-10-12。本轮以154节、642个内部话题为起点，在十章各新增2节，并加深20个原节；现为174节、802个内部话题。160个新增话题均写明具体研究对象和推进问题。第一章范围从59项扩展至75项，原有13篇研究初稿保留；新增清单不代表新增正文已经写完。', '',
        '这一轮把机器与牌照之外的过程写入大纲：人工接续和施工协调、企业后台和债务、普通企业托管、测量的可见性、商用测试、渠道风险、家庭管理、工艺学习与跨境运营。各节以一个能够追踪的流程或冲突推进，不把更多标题当作更充分的史料。', '',
        '## 回忆材料与论文怎样改变问题', '',
        '王建宙的两部著作目前仍是已核书目、公开采访及书摘入口，原书页码尚需补读。新增胡启立《“芯”路历程》的2006首发报道及转引自序：作者具有电子工业主管和华虹董事长的双重身份，合作伙伴、市场周期和建设争议提供追档线索，但本轮没有取得整本回忆录。SIM卡价格与节约估算保留为待验算问题。', '',
        '侯自强2001访谈呈现当时对新网通、铁通及拆分的公开主张，不能由后来改革结果反推其发言已是获批方案。2010融合访谈仅读第1页，主要用于定位技术、产业链与准入的不同层次。吴基传、刘彩与朱高峰的材料继续按行业主管、政策参与者、传记及采访的不同体裁使用，不统称国企领导回忆录。', '',
        '学术新增包括Harwit两篇研究的摘要、Yu Hong和Hong Shen两篇不同作者的论文指定页、境内拓扑测量论文的方法页、国内路由安全研究摘要、Gao的WAPI研究摘要及科学院工业互联网公开前言摘要。框架转化成需要检验的问题；未读全文的论文不采用其具体估计或案例细节作为定论。', '',
        '新增北京1982会议纪要及山东、济南核算材料提供工程和企业制度的具体入口；学校手机通知、环保标准发布页与产品召回公告提供后期对照。规划不等于完成，内部结算价不等于用户资费，标准发布不证明单站达标，企业召回公告不证明用户均获补偿。', '',
        '## 十章本轮增补位置', '',
        '|章|新增小节|加深原节|', '|---|---|---|',
    ]
    for c in sorted({s['chapter_id'] for s in sections}):
        selected = [r for r in changes if lookup[r['section_id']]['chapter_id'] == c]
        def links(kind):
            return '；'.join(f"[{section_number(lookup[r['section_id']])} {lookup[r['section_id']]['title']}](../book/SECTION_OUTLINE.md#{r['section_id'].lower()})" for r in selected if r['change_type'] == kind)
        lines.append(f"|第{int(c[2:])}章|{links('new_section')}|{links('deepened_section')}|")
    lines.extend(['', '## 新增文献及实际阅读范围', ''])
    for r in refs.values():
        if 229 <= int(r['id'][1:]) <= 247:
            lines.append(f"- **{r['id']}** [{r['title']}]({r['url']})；{r['creator']}；{r['verification']}；{r['locator']}。{r['notes']}")
    for c in sorted({s['chapter_id'] for s in sections}):
        lines.extend(['', f"## 第{int(c[2:])}章：具体缺口与扩展", ''])
        for r in changes:
            s = lookup[r['section_id']]
            if s['chapter_id'] != c:
                continue
            kind = '新增小节' if r['change_type'] == 'new_section' else '加深原节'
            lines.extend([
                f"### {kind}：[{section_number(s)} {s['title']}](../book/SECTION_OUTLINE.md#{s['id'].lower()})", '',
                f"原纲缺口：{r['gap_identified']}", '',
                f"新增话题：{r['added_scope'].replace(';', '；')}。", '',
                f"史料入口：{'、'.join(r['source_ids'].split(';'))}。", '',
                f"阅读及论证边界：{r['reading_boundary']}", '',
            ])
    lines.extend([
        '## 继续补读与取舍', '',
        '优先补胡启立回忆录原书及王建宙书摘页码、未读论文正文；补操作法和职工转岗、城市施工与竣工、重组后台和交易债务、渠道合同及召回办理、学校实施、芯片采购及工程培训、工厂互操作和跨境运营合同。材料不足的案例暂不写成现场故事。', '',
        '新节并不要求全书变成同等篇幅的百科。原有供给、经营权、互联和标准主线继续推进；本轮增补用劳动过程、合同和使用条件解释主线，正式成稿时按证据和论证决定篇幅。', '',
        '结构来源：[第三轮变更CSV](outline-expansion-v3.csv)及[小节总表](section-outline-v1.csv)。永久ID继续有效，显示节号随插入调整。',
    ])
    (ROOT / 'research/outline-expansion-v3.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    rows = read_table('research/chapter-plan-v1.csv')
    sections = read_table('research/section-outline-v1.csv')
    sections.sort(key=lambda s: (s['chapter_id'], int(s['section_order'])))
    render_chapter_one(sections)
    render_expansion(sections)
    render_expansion_v3(sections)
    for row in rows:
        row['sections'] = ';'.join(
            f"{section_number(s)} {s['title']}" for s in sections if s['chapter_id'] == row['id']
        )
        row['source_ids'] = ';'.join(dict.fromkeys(
            row['source_ids'].split(';') + [
                source for s in sections if s['chapter_id'] == row['id']
                for source in s['source_ids'].split(';') if source
            ]
        ))
    with (ROOT / 'research/chapter-plan-v1.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    subtopic_count = render_sections(rows, sections)
    lines = [
        "# 十章写作方案：连接的秩序", "",
        "版本：2026-10-12。十章是本轮依用户明确要求重编的工作方案，供审阅与继续扩写；不声称逐字恢复了原研讨的最终十章目录。", "",
        "## 与原研讨及现有初稿的关系", "",
        "重新读取[原研讨](https://chatgpt.com/share/6acbdf37-d43c-83ec-8e5e-830d4374a125?ogimg=plain)：第二轮答复有“六篇，约24章”的早期建议；第十六轮的方法讨论提出序幕、五个历史分期与终篇，并明确说“不是最终章节目录”。这些篇、分期和章不能混作一个层级。目前未定位到一份逐章列明的十章总目录，因此本方案公开记录其重编性质。研讨仅用于确认研究范围和写作意图，不作为历史事实的独立证据。", "",
        "原仓库的五篇实际上是专题稿的收纳分组，且与研讨末尾的五个历史分期并不完全一致。现改为导论加十章的阅读结构，综合结尾归入第十章末。既有文件路径保留，供引用和研究记录继续定位；目录里的章号才是本轮书稿结构。", "",
        "17个研讨主题仍全部保留，18篇既有专题文本作为章内材料，不等于18个完成的章节。T02、T16、T17服务全书的编纂、方法和出版定位；其余主题进入十章。第二章已开始按独立话题编纂，当前进度以章内目录和逐题清单为准，不能把导论或部分初稿冒充完整改革史。", "",
        f"十章现已细化为{len(sections)}个小节、{subtopic_count}个三级话题，每节的问题、内部话题、叙事、史料与衔接见[详细小节大纲](SECTION_OUTLINE.md)。", "",
        "## 全书怎样连起来", "",
        "叙事依次追问：连接如何从稀缺资源扩大供给；经营权如何重组；互联网和不同进入者如何出现；网络间的连接为何需要谈判；标准怎样塑造部署；手机产业与居民生活怎样变化；芯片与工业连接怎样改变技术和组织条件。", "",
        "十章不是十个互不重叠的年代。前五章主要推进供给、改革、接入和竞争的形成，后五章推进大规模移动通信、产业与社会变化。跨时期专题在主要章节讲完整过程，其余位置交叉引用。第一、二章的早期材料须先补，不能让后三十年的材料丰富程度压倒全书起点。", "",
        "|章|标题|主要问题与时间范围|", "|---|---|---|",
    ]
    summary = [
        "# 全书目录", "",
        "书名：**连接的秩序：通信网络与现代中国的形成**。英文项目名：**The Order of Connectivity**。", "",
        "逐章的问题、写法与缺件见[十章方案](CHAPTER_PLAN.md)，每个小节的问题及内部话题见[详细大纲](SECTION_OUTLINE.md)，原研讨范围见[17主题史料总纲](../research/source-outline-v1.md)。以下小节均可点击；既有稿件是研究材料，不表示整章完成。文件夹名称保留原研究阶段的分组。", "",
        "## 导论：把通信放回历史", "",
        "- [从技术代际到连接的制度](00-introduction/topics/01-object-and-institutions.md)",
        "- [多重时间、技术系统与可复核的历史解释](00-introduction/topics/02-method-and-evidence.md)",
    ]
    for number, row in enumerate(rows, 1):
        lines.append(f"|[第{number}章](#{row['id'].lower()})|{row['title']}|{row['question']} {row['period']}。|")
        summary.extend([
            "", f"## 第{number}章：{row['title']}", "",
            f"{row['period']}。{row['question']}", "",
            f"[本章写法](CHAPTER_PLAN.md#{row['id'].lower()})。[本章详细大纲](SECTION_OUTLINE.md#{row['id'].lower()})。", "",
            "小节目录：", "",
        ])
        for section in sections:
            if section['chapter_id'] == row['id']:
                summary.append(f"- [{section_number(section)}　{section['title']}](SECTION_OUTLINE.md#{section['id'].lower()})")
        summary.extend(['', '已有材料：', ''])
        for path in row["manuscripts"].split(";"):
            title = manuscript_title(path)
            summary.append(f"- [{title}]({Path(path).relative_to('book')})")
        if row["id"] == "CH02":
            summary.extend(["", "本章尚缺独立完整正文；现有链接是制度材料入口，联通成立及历次拆分重组须补写。"])
    for number, row in enumerate(rows, 1):
        lines.extend([
            "", f'<a id="{row["id"].lower()}"></a>', "",
            f"## 第{number}章：{row['title']}", "",
            f"时间重心：{row['period']}。", "", f"**核心问题**：{row['question']}", "",
            f"**叙事入口**：{row['opening']}", "", "**拟定节次**：", "",
        ])
        lines.extend(
            f"- [{section_number(s)}　{s['title']}](SECTION_OUTLINE.md#{s['id'].lower()})"
            for s in sections if s['chapter_id'] == row['id']
        )
        lines.extend([
            "", f"**怎样写**：{row['narrative']}", "",
            f"**与其他章的边界**：{row['boundary']}", "",
            "**已有文本**：", "",
        ])
        for path in row["manuscripts"].split(";"):
            title = manuscript_title(path)
            lines.append(f"- [{title}]({Path(path).relative_to('book')})")
        lines.extend([
            "", f"**史料入口**：研讨主题{'、'.join(row['topic_ids'].split(';'))}；现有登记编号{'、'.join(row['source_ids'].split(';'))}。标题、原文地址、版本及实际阅读范围见[文献表](../references/references.csv)；具体子问题与缺件见[17主题史料总纲](../research/source-outline-v1.md)。这些是可用入口，不是已充分覆盖本章的宣告。", "",
            f"**优先补证及证据边界**：{row['remaining_work']}",
        ])
    lines.extend([
        "", "## 从专题稿变成章稿", "",
        "每章采用原研讨提出的六层叙事：有出处的场景、结构背景、参与者冲突、决策过程、可观察结果、长期意义。材料不支持场景时，从原文件或公开数据进入；不补写虚构人物、对话与心理。章内不按企业逐条堆小传，每节要推进同一个核心问题。", "",
        "先把既有专题稿按节次建立段落归属，再统一时间线、术语和指标，补过渡并删重复。涉及同一重组、牌照或产品的段落只设一个主叙述位置；其他章说明其与本章问题的关系，并给出交叉引用。", "",
        "补证优先序：第一、二章的原工程与改革材料；第三至六章的准入、合同、历史网络和标准实施；第七至十章的生产、家庭与工厂对照。查不到的材料继续标未知，不能用研讨中的评价或现有目录补足因果关系。", "",
        "一章形成完整初稿，需要主问题对应的连续叙事、可定位引用、重大争议与反例、数量口径及证据局限。最终还需要全书交叉核查、技术与学术审校；十章目录和初版史料大纲的建立都不是全书完成。", "",
        "结构来源：[章节方案CSV](../research/chapter-plan-v1.csv)与[小节大纲CSV](../research/section-outline-v1.csv)。小节标题以小节表为准，运行`python3 scripts/build_chapter_plan.py`同步章级节次并生成详细大纲、本文件及目录，再运行`python3 scripts/validate.py`核查关联。",
    ])
    (ROOT / "book/CHAPTER_PLAN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "book/SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"Built {len(rows)} chapters, {len(sections)} sections, {subtopic_count} subtopics and their reading index.")


if __name__ == "__main__":
    main()
