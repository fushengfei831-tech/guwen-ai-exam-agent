# -*- coding: utf-8 -*-
"""
把 276 题题库按「题型」拆成 3 个独立文件，用于 Dify 元数据过滤。
输出目录：拆分明细/
  名词解释.txt（105 题）
  简答题.txt（49 题）
  论述题.txt（122 题）
格式与原 完美版.txt 保持一致，保证检索质量。
"""
import csv
import os
import re
from collections import defaultdict

SRC = "题库_结构化.csv"
OUTDIR = "拆分明细"
os.makedirs(OUTDIR, exist_ok=True)

rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
groups = defaultdict(list)
for r in rows:
    groups[r["题型"]].append(r)

HEAD = "# 中国古代文学史题库 · {t}（共 {n} 题）\n\n"

total = 0
for t, rs in sorted(groups.items(), key=lambda x: -len(x[1])):
    fname = t + ".txt"
    path = os.path.join(OUTDIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(HEAD.format(t=t, n=len(rs)))
        for i, r in enumerate(rs, 1):
            f.write("## %d. %s：%s\n" % (i, r["题型"], r["题干"]))
            f.write("- 科目：%s\n" % r["科目"])
            f.write("- 时期：%s\n" % r["时期"])
            f.write("- 题型：%s\n" % r["题型"])
            f.write("\n【题干】\n%s\n" % r["题干"])
            f.write("\n【参考答案】\n%s\n" % r["参考答案"])
            pts = [p.strip() for p in r["答题要点"].split("|") if p.strip()]
            f.write("\n【答题要点】\n")
            for p in pts:
                f.write("- %s\n" % p)
            f.write("\n---\n\n")
    size = os.path.getsize(path)
    total += size
    print("%-12s %3d 题  %7.1f KB  →  %s" % (t, len(rs), size / 1024, path))

print("\n合计 %.1f KB，输出目录：%s" % (total / 1024, OUTDIR))
print("\n提示：这三个文件需要分别打上元数据 题型=名词解释 / 简答题 / 论述题")
