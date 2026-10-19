# -*- coding: utf-8 -*-
"""
用 LLM-as-judge 判定要点覆盖率（替代字符串匹配）。

方法要点（面试可讲）：
  1. 每次只把「一道题的采分点 + 两份回答」交给裁判模型，逐条判断是否覆盖；
  2. 随机交换两份回答的呈现顺序（回答1/回答2），消除位置偏差；
  3. 要求只输出 JSON，便于机器解析；
  4. 与规则匹配法交叉验证，计算一致率。
"""
import json
import os
import random
import re
import time
import urllib.request

BASE = "http://localhost/v1"
JUDGE_KEY = os.environ["KEY_A"]          # 用无知识库的 A 组当裁判，避免被题库污染
SRC = "ab_results.json"
OUT = "judge_results.json"

THINK = re.compile(r"<think>.*?</think>", re.S)
random.seed(20261010)

PROMPT = """你是中国古代文学专业的阅卷老师。请逐条判断下面两份回答对每个采分点的覆盖情况。

【题目】{stem}

【采分点】（共 {n} 条）
{points}

【回答甲】
{ans1}

【回答乙】
{ans2}

判定口径：
- 覆盖 = 回答表达了该采分点的核心意思，**措辞不同也算覆盖**，不要求字面一致；
- 只沾边、缺关键信息、或说错，记为未覆盖；
- 两份回答各自独立判断，互不参照。

只输出一个 JSON，不要任何解释文字，格式如下（数组长度必须等于 {n}）：
{{"甲":[{ones}],"乙":[{ones}]}}"""


def strip_think(t):
    t = THINK.sub("", t)
    return re.sub(r"<!--dify-deepseek-reasoning-->", "", t).strip()


def chat(query, timeout=300):
    payload = {"query": query, "inputs": {}, "response_mode": "streaming",
               "user": "judge"}
    req = urllib.request.Request(
        BASE + "/chat-messages",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + JUDGE_KEY,
                 "Content-Type": "application/json"},
        method="POST")
    ans = ""
    with urllib.request.urlopen(req, timeout=timeout) as resp:
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
    return strip_think(ans)


def parse_json(txt, n):
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    out = {}
    for k in ("甲", "乙"):
        v = d.get(k)
        if not isinstance(v, list) or len(v) != n:
            return None
        out[k] = [1 if x else 0 for x in v]
    return out


def parse_points(text):
    out = []
    for line in (text or "").split("\n"):
        line = line.strip()
        if line.startswith("·"):
            line = line[1:].strip()
        if line:
            out.append(line)
    return out


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    results = []
    for i, d in enumerate(data, 1):
        pts = parse_points(d["points"])
        n = len(pts)
        if n == 0:
            continue
        a_ans, b_ans = d["A"]["final"], d["B"]["final"]
        # 随机决定谁当「甲」，消除位置偏差
        a_is_first = random.random() < 0.5
        first, second = (a_ans, b_ans) if a_is_first else (b_ans, a_ans)
        q = PROMPT.format(
            stem=d["stem"],
            n=n,
            points="\n".join("%d. %s" % (j + 1, p) for j, p in enumerate(pts)),
            ans1=first[:2500] if first else "（空）",
            ans2=second[:2500] if second else "（空）",
            ones=",".join(["0"] * n))
        verdict = None
        for attempt in range(3):
            try:
                raw = chat(q)
                verdict = parse_json(raw, n)
                if verdict:
                    break
            except Exception:
                pass
            time.sleep(2)
        if not verdict:
            print("[%2d] 判定失败：%s" % (i, d["stem"][:24]), flush=True)
            results.append({"no": d["no"], "period": d["period"], "type": d["type"],
                            "stem": d["stem"], "n_points": n,
                            "A_cov": None, "B_cov": None,
                            "A_detail": "", "B_detail": "", "error": "judge failed"})
            continue
        first_cov = verdict["甲"]
        second_cov = verdict["乙"]
        a_cov = first_cov if a_is_first else second_cov
        b_cov = second_cov if a_is_first else first_cov
        results.append({
            "no": d["no"], "period": d["period"], "type": d["type"],
            "stem": d["stem"], "n_points": n, "a_is_first": a_is_first,
            "A_cov": sum(a_cov) / n, "B_cov": sum(b_cov) / n,
            "A_detail": "".join(map(str, a_cov)),
            "B_detail": "".join(map(str, b_cov)),
        })
        print("[%2d/%d] %s | A %.0f%% %s | B %.0f%% %s"
              % (i, len(data), d["stem"][:20],
                 sum(a_cov) / n * 100, "".join(map(str, a_cov)),
                 sum(b_cov) / n * 100, "".join(map(str, b_cov))), flush=True)

    json.dump(results, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    ok = [r for r in results if r.get("A_cov") is not None]
    print("\n完成：%d 条有效判定" % len(ok))
    if ok:
        print("A 组平均覆盖率 %.1f%%" % (sum(r["A_cov"] for r in ok) / len(ok) * 100))
        print("B 组平均覆盖率 %.1f%%" % (sum(r["B_cov"] for r in ok) / len(ok) * 100))


if __name__ == "__main__":
    main()
