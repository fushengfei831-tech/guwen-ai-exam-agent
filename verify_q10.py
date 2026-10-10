# -*- coding: utf-8 -*-
"""
验证元数据过滤是否修复了第 10 题（梅尧臣）：
  1. 用同一道题重跑 A 组与 B 组
  2. 用 LLM-as-judge 判定要点覆盖率
  3. 与修复前的数据对比
"""
import json
import os
import re
import urllib.request

BASE = "http://localhost/v1"
KEY_A = os.environ["KEY_A"]
KEY_B = os.environ["KEY_B"]

THINK = re.compile(r"<think>.*?</think>", re.S)

POINTS = [
    "好为新奇，力避陈熟，取材个人化、生活化、琐碎化",
    "平淡其表，深邃其里，古淡，老树著花之美",
    "构思奇巧，用意深远，感情深厚，寓奇峭于朴素，外枯中膏",
    "题材广泛，分干预政治和日常生活两类",
]
QUERY = "简述梅尧臣诗歌的艺术特点。"


def strip_think(t):
    t = THINK.sub("", t)
    return re.sub(r"<!--dify-deepseek-reasoning-->", "", t).strip()


def chat(key, query, user="verify"):
    payload = {"query": query, "inputs": {}, "response_mode": "streaming", "user": user}
    req = urllib.request.Request(
        BASE + "/chat-messages",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST")
    ans, usage, nret, docs = "", None, 0, []
    with urllib.request.urlopen(req, timeout=300) as resp:
        for line in resp:
            s = line.decode("utf-8", "replace").strip()
            if not s.startswith("data:"):
                continue
            b = s[5:].strip()
            if not b or b == "[DONE]":
                continue
            try:
                ev = json.loads(b)
            except Exception:
                continue
            if ev.get("event") in ("message", "agent_message"):
                ans += ev.get("answer", "") or ""
            elif ev.get("event") == "message_end":
                md = ev.get("metadata", {}) or {}
                usage = md.get("usage")
                rr = md.get("retriever_resources", []) or []
                nret = len(rr)
                docs = [(x.get("document_name"), round(x.get("score", 0), 3),
                         (x.get("content") or "")[:60].replace("\n", " "))
                        for x in rr]
    return strip_think(ans), usage, nret, docs


JUDGE = """你是中国古代文学专业的阅卷老师。请逐条判断下面两份回答对每个采分点的覆盖情况。

【题目】{stem}

【采分点】（共 {n} 条）
{points}

【回答甲】
{a}

【回答乙】
{b}

判定口径：
- 覆盖 = 回答表达了该采分点的核心意思，措辞不同也算覆盖，不要求字面一致；
- 只沾边、缺关键信息、或说错，记为未覆盖；
- 两份回答各自独立判断，互不参照。

只输出 JSON，不要任何解释文字，格式（数组长度必须等于 {n}）：
{{"甲":[{z}],"乙":[{z}]}}"""

old = {d["no"]: d for d in json.load(open("ab_results.json", encoding="utf-8"))}
o = old[10]

print("=" * 70)
print(" 第 10 题「简述梅尧臣诗歌的艺术特点」修复验证")
print("=" * 70)
print("\n修复前：A 组 100%（1111） / B 组 50%（0101）\n")

a_ans, a_u, a_r, a_docs = chat(KEY_A, QUERY)
b_ans, b_u, b_r, b_docs = chat(KEY_B, QUERY)

print("重跑 A 组：prompt %s tokens，引用片段 %d，回答 %d 字"
      % ((a_u or {}).get("prompt_tokens"), a_r, len(a_ans)))
print("重跑 B 组：prompt %s tokens，引用片段 %d，回答 %d 字"
      % ((b_u or {}).get("prompt_tokens"), b_r, len(b_ans)))
print("（修复前 B 组 prompt 为 %s tokens）"
      % ((o["B"]["usage"] or {}).get("prompt_tokens")))

print("\n--- B 组这次检索到的片段（看来自哪个文件）---")
for name, score, snippet in b_docs:
    print("  [%s] score=%.3f  %s" % (name, score, snippet))

n = len(POINTS)
q = JUDGE.format(stem=QUERY, n=n,
                 points="\n".join("%d. %s" % (i + 1, p) for i, p in enumerate(POINTS)),
                 a=a_ans[:2500], b=b_ans[:2500], z=",".join(["0"] * n))
raw = chat(KEY_A, q, user="judge2")[0]
m = re.search(r"\{.*\}", raw, re.S)
verdict = json.loads(m.group(0)) if m else None

print("\n--- 裁判判定 ---")
if verdict:
    aa = [1 if x else 0 for x in verdict["甲"]]
    bb = [1 if x else 0 for x in verdict["乙"]]
    print("A 组：%s  覆盖率 %.0f%%" % ("".join(map(str, aa)), sum(aa) / n * 100))
    print("B 组：%s  覆盖率 %.0f%%" % ("".join(map(str, bb)), sum(bb) / n * 100))
    print("对比修复前 B 组：50%%  ->  现在 %.0f%%" % (sum(bb) / n * 100))
else:
    print("裁判输出解析失败：", raw[:300])

print("\n--- B 组本次回答全文 ---")
print(b_ans)
json.dump({"A": a_ans, "B": b_ans, "A_usage": a_u, "B_usage": b_u,
           "A_ret": a_r, "B_ret": b_r, "verdict": verdict},
          open("verify_q10.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
