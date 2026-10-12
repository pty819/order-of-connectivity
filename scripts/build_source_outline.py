#!/usr/bin/env python3
"""Build the readable outline from its CSV and existing reference metadata."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_table(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    rows = read_table("research/source-outline-v1.csv")
    refs = {r["id"]: r for r in read_table("references/references.csv")}
    topics = {r["id"]: r for r in read_table("research/topics.csv")}
    lines = [
        "# 初版史料大纲：连接的秩序", "",
        "版本：2026-10-12。按原研讨17个主题排列，供核对范围和继续扩写。初版大纲已为每个主题建立子问题、正文入口、已读史料基础、叙事方向和待补证清单。大纲覆盖完整不等于每份史料已经取得或全书完成。", "",
        "正文按历史问题编排，主题顺序与章节顺序不完全相同。正文见[全书目录](../book/SUMMARY.md)，可处理结构见[大纲CSV](source-outline-v1.csv)，版本和阅读范围见[参考文献表](../references/references.csv)，具体事实关系见[证据表](claims.csv)。", "",
        "本初版将材料分为原始规范与合同、当期统计与企业披露、机构或参与者回忆、学术研究四类。摘要、目录和索引只能承担其已读范围；缺件列入任务，不作为已经核实的依据。下列每一项都保留原研讨范围，不因初稿已写到某处而删除难题。", "",
        "## 分期与编排", "",
        "1978—1993：稀缺供给、设备、建设组织与科研联网。1994—2008：进入与管辖、骨干互联、公众互联网及移动服务扩散。2009—2018：多制式、LTE融合、手机产业、平台合作和社会消费。2019—2026：共享网络、技术供给约束、产业能力与机器连接。跨时期专题保留其完整过程，最终再汇入连续叙事。", "",
        "## 范围覆盖索引", "",
        "|主题|原研讨范围|初版状态|", "|---|---|---|",
    ]
    for row in rows:
        lines.append(f"|[{row['id']}](#{row['id'].lower()})|{topics[row['id']]['topic']}|史料与写作骨架已建立；正文研究初稿|")
    for row in rows:
        lines.extend([
            "", f'<a id="{row["id"].lower()}"></a>', "",
            f"## {row['id']}　{topics[row['id']]['topic']}", "",
            f"时间范围：{row['period']}。", "", f"子问题：{row['subtopics']}。", "",
            f"叙事主线：{row['narrative']}", "", f"已读依据：{row['evidence_summary']}", "",
            "正文入口：", "",
        ])
        for path in row["manuscripts"].split(";"):
            title = (ROOT / path).read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
            lines.append(f"- [{title}](../{path})")
        lines.extend(["", "史料入口及阅读范围：", ""])
        for source in row["source_ids"].split(";"):
            ref = refs[source]
            lines.append(f"- **{source}** [{ref['title']}]({ref['url']})；{ref['verification']}；{ref['locator']}。")
        lines.extend(["", f"继续补证：{row['remaining_work']}。"])
    lines.extend([
        "", "## 初版后的工作", "",
        "按研究缺口补原件与对照，再扩写为章节。优先处理早期通信供给、产业采购与供应链、完整监管版本、经营合同和用户材料；随后统一跨章时间线与术语，检验叙事中的因果关系。终篇需要由全书比较得出，不能由个案成功、失败或某份政策的目标提前写定。", "",
        "公共仓：[order-of-connectivity](https://github.com/pty819/order-of-connectivity)。本次只确认初版史料纲目覆盖，不将其替代全部史实核验、详细工程史或外部学术审稿。",
    ])
    (ROOT / "research/source-outline-v1.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Built {len(rows)} topic outlines; run scripts/validate.py to check their relationships.")


if __name__ == "__main__":
    main()
