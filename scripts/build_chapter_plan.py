#!/usr/bin/env python3
"""Render chapter plans, detailed section outlines and the reading index."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_table(path):
    with (ROOT / path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def section_number(row):
    return f"{int(row['chapter_id'][2:])}.{int(row['id'].split('-S')[1])}"


def render_sections(chapters, sections):
    refs = {r['id']: r for r in read_table('references/references.csv')}
    lookup = {section_number(s): s for s in sections}
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
            for i, topic in enumerate(s['subtopics'].split(';'), 1):
                lines.append(f'- {label}.{i}　{topic}')
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
                for number in s['cross_refs'].split(';'):
                    target = lookup[number]
                    targets.append(f"[{number}　{target['title']}](#{target['id'].lower()})")
                lines.extend(['', '**衔接与分工**：与' + '、'.join(targets) + '互相参照；同一事件以其主要小节叙述为准，本节只展开与自身问题有关的部分。'])
    lines.extend([
        '', '## 扩写和整合顺序', '',
        '先为每节整理时间线、参与者、原文件、可比指标及争议，再将三级话题写成相互连接的段落。不是每个三级话题都必须成为正式正文标题；最终正文按论证和阅读节奏合并，但研究范围不能因排版被删。', '',
        '优先补第一、二章的工程、资费、成立及交割原件；随后补第三至六章的服务、合同、历史拓扑与标准实施；最后补第七至十章的供应链、家庭、资本和工厂对照。已有稿可先归入相应小节，完成局部核验后再做全章过渡与删重。', '',
        '每章末只总结本章可支持的判断并引出下一章，第十章末进行全书综合。跨节引用不得代替证据，研究问题不预写成结论。', '',
        '结构来源：[小节大纲CSV](../research/section-outline-v1.csv)；章级来源：[十章方案CSV](../research/chapter-plan-v1.csv)。两者由`python3 scripts/build_chapter_plan.py`统一生成阅读文件，随后运行`python3 scripts/validate.py`核对。',
    ])
    (ROOT / 'book/SECTION_OUTLINE.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return count


def main():
    rows = read_table('research/chapter-plan-v1.csv')
    sections = read_table('research/section-outline-v1.csv')
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
        "17个研讨主题仍全部保留，18篇既有专题文本作为章内材料，不等于18个完成的章节。T02、T16、T17服务全书的编纂、方法和出版定位；其余主题进入十章。第二章目前只有制度材料入口，不能把导论冒充完整改革史。", "",
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
            title = (ROOT / path).read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
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
            title = (ROOT / path).read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
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
