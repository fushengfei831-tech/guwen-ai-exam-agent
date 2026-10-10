# -*- coding: utf-8 -*-
"""
硅基流动 API 密钥自测工具
直接向 api.siliconflow.cn 发一次真实的嵌入请求，把服务器的原始回复打印出来。

用法：双击同目录的「测试密钥.bat」，或命令行 python test_siliconflow.py
"""
import json
import urllib.error
import urllib.request

URL = "https://api.siliconflow.cn/v1/embeddings"
MODEL = "BAAI/bge-m3"


def main():
    print("=" * 56)
    print(" 硅基流动 API 密钥自测")
    print("=" * 56)
    print("\n【重要】测试前请先断开 VPN，否则测试结果不准。\n")

    key = input("请粘贴你的硅基流动密钥（sk- 开头），然后按回车：\n> ").strip()
    if not key:
        print("没有输入密钥，退出。")
        return

    print("\n正在测试…… 模型：%s" % MODEL)
    print("地址：%s\n" % URL)

    payload = {
        "model": MODEL,
        "input": ["床前明月光，疑是地上霜。"],
        "encoding_format": "float",
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.load(r)
        vec = data.get("data", [{}])[0].get("embedding", [])
        print("✅ 成功！密钥可用。")
        print("   返回向量维度：%d" % len(vec))
        print("   说明：Dify 里的 embedding 模型配置没问题，")
        print("   回 Dify 重新处理文档即可。")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print("❌ 失败，HTTP 状态码：%d" % e.code)
        print("   服务器原始回复：")
        print("   " + body[:800])
        print()
        if e.code == 401:
            print("   判断：密钥无效或已删除 → 去控制台重新生成一个密钥。")
        elif e.code == 403:
            print("   判断：权限不足（官方定义：最常见是该模型需要实名认证）。")
            print("     1) 账号没做实名认证            → 去控制台做实名")
            print("     2) 该模型不在你的可用列表里    → 看下面的可用模型列表")
        elif e.code == 404:
            print("   判断：模型名不对 → 必须是 BAAI/bge-m3（大小写敏感）。")
        elif e.code == 429:
            print("   判断：请求太频繁或额度用尽 → 等一会儿或看额度。")
        else:
            print("   判断：按上面服务器回复的内容处理。")
    except Exception as e:
        print("❌ 网络层错误：%r" % (e,))
        print("   说明连都没连上。检查：VPN 是否把国内网站也代理了、网络是否正常。")

    # ========== 附加：列出你这个账号可以用的 embedding 模型 ==========
    print("\n" + "=" * 56)
    print(" 你的账号可用的 embedding 模型列表")
    print("=" * 56)
    try:
        req2 = urllib.request.Request(
            "https://api.siliconflow.cn/v1/models",
            headers={"Authorization": "Bearer " + key},
            method="GET",
        )
        with urllib.request.urlopen(req2, timeout=40) as r:
            data = json.load(r)
        ids = [m.get("id", "") for m in data.get("data", [])]
        emb = [i for i in ids if ("embed" in i.lower() or "bge" in i.lower()
                                  or "Embedding" in i)]
        print("共 %d 个模型，其中 embedding 类 %d 个：" % (len(ids), len(emb)))
        for i in emb:
            mark = "  ← 推荐用这个" if i == "BAAI/bge-m3" else ""
            print("   %s%s" % (i, mark))
        if not emb:
            print("   （没有列出 embedding 模型，可能需要在控制台先开通）")
        print("\n把 Dify 里的 Text Embedding 换成上面列表中的任意一个即可。")
    except Exception as e:
        print("获取模型列表失败：%r" % (e,))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
    input("\n按回车键关闭窗口...")
