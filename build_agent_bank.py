# -*- coding: utf-8 -*-
"""
生成 Agent 可直接读取的题库缓存文件：
  1. 题库缓存.md          —— 单文件，按时期分节 + 顶部索引（可直接替换 Agent 里那份）
  2. 题库_按时期/          —— 按时期拆成 8 个文件（Agent 只需读相关的一个）
"""
import csv
import os
from collections import defaultdict

SRC = "题库_结构化.csv"
SINGLE = "题库缓存.md"
SPLIT_DIR = "题库_按时期"
os.makedirs(SPLIT_DIR, exist_ok=True)

rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
ORDER = ["先秦", "秦汉", "魏晋南北朝", "隋唐五代", "宋代", "辽金元", "明代", "清代"]

by_period = defaultdict(list)
for r in rows:
    by_period[r["时期"]].append(r)

periods = [p for p in ORDER if p in by_period] + \
          [p for p in by_period if p not in ORDER]


def render_entry(i, r):
    pts = [p.strip() for p in r["答题要点"].split("|") if p.strip()]
    s = []
    s.append("### %d. %s：%s\n" % (i, r["题型"], r["题干"]))
    s.append("**题型**：%s　|　**时期**：%s\n" % (r["题型"], r["时期"]))
    s.append("\n**【题干】**\n%s\n" % r["题干"])
    s.append("\n**【参考答案】**\n%s\n" % r["参考答案"])
    s.append("\n**【答题要点】**\n")
    for p in pts:
        s.append("- %s\n" % p)
    s.append("\n")
    return "".join(s)


HEAD = """# 古代文学题库缓存（按时期索引）

> **给 Agent 的使用说明**
> 1. 用户输入朝代/作家后，先判断它属于哪个**时期**，再到对应小节里取题。
> 2. 只输出该题的 **【题干】** 一行，**立即停止**，不要输出参考答案或答题要点。
> 3. 若该时期找不到合适题目，直接回复：「这题我这边没查到可靠材料，换个朝代或作家再试试？」，**绝不自己编题**。
> 4. 判卷时使用该题的 **【参考答案】** 与 **【答题要点】** 作为评分依据。

## 时期索引

| 时期 | 题数 | 在本文中的位置 |
| --- | --- | --- |
"""

for p in periods:
    HEAD += "| %s | %d | 见下方「%s」小节 |\n" % (p, len(by_period[p]), p)

HEAD += "\n**时期对应的代表作家/作品（用于判断用户输入）**\n\n"
HEAD += "| 时期 | 代表作家/作品 |\n| --- | --- |\n"
REP = {
    "先秦": "《诗经》《楚辞》《左传》《论语》《孟子》《庄子》、神话、上古歌谣",
    "秦汉": "《史记》、汉乐府、《古诗十九首》、贾谊、司马相如、汉赋",
    "魏晋南北朝": "三曹、陶渊明、谢灵运、鲍照、庾信、《世说新语》、《搜神记》、永明体、志怪小说",
    "隋唐五代": "初唐四杰、李白、杜甫、王维、白居易、韩愈、柳宗元、李商隐、唐传奇、花间词、南唐词人",
    "宋代": "苏轼、欧阳修、柳永、李清照、辛弃疾、陆游、杨万里、江西诗派、话本、诸宫调",
    "辽金元": "元好问、关汉卿、王实甫、马致远、《西厢记》、《汉宫秋》、《倩女离魂》、元曲四大家",
    "明代": "《三国演义》《水浒传》《西游记》《金瓶梅》、汤显祖、归有光、唐宋派、公安派、竟陵派",
    "清代": "《红楼梦》《儒林外史》《聊斋志异》、纳兰性德、桐城派、龚自珍",
}
for p in periods:
    HEAD += "| %s | %s |\n" % (p, REP.get(p, "—"))

HEAD += "\n---\n\n"

# ---------- 单文件 ----------
with open(SINGLE, "w", encoding="utf-8") as f:
    f.write(HEAD)
    for p in periods:
        f.write("# %s（共 %d 题）\n\n" % (p, len(by_period[p])))
        for i, r in enumerate(sorted(by_period[p], key=lambda x: int(x["题号"])), 1):
            f.write(render_entry(i, r))
        f.write("\n---\n\n")
print("%-24s %7.1f KB" % (SINGLE, os.path.getsize(SINGLE) / 1024))

# ---------- 按时期拆分 ----------
for p in periods:
    path = os.path.join(SPLIT_DIR, "%s.md" % p)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# %s题库（共 %d 题）\n\n" % (p, len(by_period[p])))
        f.write("> 出题时只输出【题干】一行并停止；判卷时使用【参考答案】与【答题要点】。\n\n")
        for i, r in enumerate(sorted(by_period[p], key=lambda x: int(x["题号"])), 1):
            f.write(render_entry(i, r))
    print("%-24s %7.1f KB  %d 题" % (path, os.path.getsize(path) / 1024, len(by_period[p])))

print("\n各时期题量：", {p: len(by_period[p]) for p in periods})
