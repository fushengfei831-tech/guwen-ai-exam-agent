# -*- coding: utf-8 -*-
"""
题库重复命题精确审计（v2）
先剥掉题干里的模板套话，只保留知识点本体，再比对。
例：
  「简述梅尧臣诗歌的艺术特点」→ 梅尧臣诗歌
  「梅尧臣诗歌有何特点？」    → 梅尧臣诗歌      → 同一知识点 ✓
  「谈谈《诗经》的艺术成就」  → 诗经
  「《庄子》的艺术成就表现在什么地方」→ 庄子    → 不同知识点 ✗
"""
import csv
import itertools
import re

TEMPLATE = [
    "名词解释", "简述", "简答", "简析", "试简析", "试述", "试论", "试说明", "试分别",
    "论述", "略述", "谈谈", "分析", "评价", "概述", "简说", "说明", "简论", "举例说明",
    "艺术特色", "艺术成就", "艺术特点", "艺术风格", "艺术表现", "思想内容", "主要内容",
    "文学特点", "文学价值", "主要内容是", "有何特点", "有何特色", "有何贡献", "有何异同",
    "有什么", "是什么", "是怎样", "有哪些", "主要表现在", "表现在", "表现在哪些方面",
    "主要特点", "主要特色", "主要成就", "主要贡献", "主要观点", "主要内容",
    "特点", "特色", "贡献", "成就", "地位", "影响", "作用", "价值", "优点", "得失",
    "内容", "情况", "原因", "意义", "手法", "风格", "方式", "分类", "保存情况",
    "作者是谁", "作者", "是谁", "哪些", "如何", "怎样", "什么", "怎样理解",
    "并举出", "举出", "代表作", "代表作品", "及其", "以及", "以及其", "和", "与", "的",
    "请", "并", "在", "上", "中", "了", "是", "有", "为", "对", "从", "到", "个",
    "简", "述", "评", "论", "谈", "说", "问", "答",
]

rows = list(csv.DictReader(open("题库_结构化.csv", encoding="utf-8-sig")))


def topic(stem):
    s = stem or ""
    s = re.sub(r"[《》〈〉“”\"'（）()\s，。？：、；！,\.\?:;!]", "", s)
    # 先抽书名号里的内容（最可靠的知识点标识），保留为标记
    titles = re.findall(r"[《〈]([^》〉]+)[》〉]", stem or "")
    body = s
    for t in TEMPLATE:
        body = body.replace(t, "")
    key = body.strip()
    return (key, tuple(sorted(set(titles))))


def sim(a, b):
    """本体字符重合度（以较短者为准）"""
    if not a or not b:
        return 0.0
    ba = set(a[i:i + 2] for i in range(len(a) - 1)) or set(a)
    bb = set(b[i:i + 2] for i in range(len(b) - 1)) or set(b)
    return len(ba & bb) / min(len(ba), len(bb))


items = []
for r in rows:
    k, titles = topic(r["题干"])
    items.append({"no": r["题号"], "type": r["题型"], "period": r["时期"],
                  "stem": r["题干"], "key": k, "titles": titles})

# 知识点相同 = 本体高度重合 或 书名号内容完全一致（且本体也重合）
groups = []
used = set()
for a, b in itertools.combinations(items, 2):
    if a["no"] in used and b["no"] in used:
        continue
    s = sim(a["key"], b["key"])
    title_same = bool(a["titles"]) and a["titles"] == b["titles"]
    ok = (s >= 0.75) or (title_same and s >= 0.4)
    if ok:
        groups.append((s, a, b))
        used.add(a["no"])
        used.add(b["no"])

print("=" * 74)
print(" 题库重复命题精确审计")
print("=" * 74)
print("题库总题数：%d" % len(rows))
print("判定为「同一知识点」的题组：%d 组，涉及 %d 道题（占 %.0f%%）"
      % (len(groups), len(used), 100.0 * len(used) / len(rows)))
print()

cross = [g for g in groups if g[1]["type"] != g[2]["type"]]
same = [g for g in groups if g[1]["type"] == g[2]["type"]]
print("其中【跨题型】重复（检索最容易搞错）：%d 组" % len(cross))
print("其中【同题型】重复：%d 组" % len(same))
print()
print("--- 跨题型重复明细（前 25 组）---")
for s, a, b in sorted(cross, key=lambda x: -x[0])[:25]:
    print("  本体重合 %.2f ｜ %s [%s] %s   ↔   %s [%s] %s"
          % (s, a["no"], a["type"], a["stem"][:26], b["no"], b["type"], b["stem"][:26]))
print()
print("--- 同题型重复明细（前 15 组）---")
for s, a, b in sorted(same, key=lambda x: -x[0])[:15]:
    print("  本体重合 %.2f ｜ %s [%s] %s   ↔   %s [%s] %s"
          % (s, a["no"], a["type"], a["stem"][:26], b["no"], b["type"], b["stem"][:26]))
print()
mc = [g for g in groups if "梅尧臣" in g[1]["stem"] or "梅尧臣" in g[2]["stem"]]
print("--- 梅尧臣那组是否被准确识别 ---")
for s, a, b in mc:
    print("  ✓ 重合 %.2f：%s [%s] %s  ↔  %s [%s] %s"
          % (s, a["no"], a["type"], a["stem"], b["no"], b["type"], b["stem"]))
