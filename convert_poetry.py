# -*- coding: utf-8 -*-
"""
把 chinese-poetry 的 JSON 语料，转换成 Dify 知识库能直接上传的 txt。

特点：压缩包（.zip）不用解压，本工具可以直接读。

用法（二选一）：
  1. 双击同目录下的「一键转换语料.bat」
  2. 命令行执行： python convert_poetry.py

转换结果默认输出到： D:\古文语料_成品\
"""
import json
import os
import zipfile

# ============ 1. 路径设置（如果自动找不到，请手动改这里） ============
OUT_DIR = r"D:\古文语料_成品"

# 脚本会在这些位置找「语料文件夹」或「chinese-poetry 压缩包」
SEARCH_ROOTS = [
    r"D:\古文语料",
    r"D:\chinese-poetry",
    "D:\\",
    r"C:\Users\HUAWEI\Desktop",
    r"C:\Users\HUAWEI\Downloads",
    r"C:\Users\HUAWEI\Documents",
]

# 压缩包文件名里包含这些字，就认为它是目标语料包
ZIP_HINTS = ("chinese-poetry", "chinese_poetry", "古文语料", "古诗词")

# 单个 txt 的体积上限（超过就自动分下一个文件），
# 8MB 是为了不超过 Dify 知识库的单文件上传限制
MAX_BYTES = 8 * 1024 * 1024

# 不处理的文件夹（这些不是正文数据）
SKIP_DIRS = {"images", ".github", "loader", "rank", "strains", ".idea", "py", "__MACOSX"}

# 字段优先级
TITLE_KEYS = ["title", "rhythmic", "chapter"]
AUTHOR_KEYS = ["author", "poet", "dynasty"]
SECTION_KEYS = ["chapter", "section", "source"]
BODY_KEYS = ["paragraphs", "content", "text", "lines", "verse", "paragraph"]
SKIP_KEYS = {"id", "strains", "tags", "_id", "index", "no", "title", "rhythmic",
             "chapter", "section", "author", "poet", "dynasty", "source",
             "paragraphs", "content", "text", "lines", "verse", "paragraph"}


# ============ 2. 自动寻找语料来源 ============
def looks_like_corpus(path):
    try:
        names = set(os.listdir(path))
    except Exception:
        return False
    return any(k in names for k in ("全唐诗", "宋词", "诗经", "楚辞", "元曲", "论语"))


def is_target_zip(name):
    low = name.lower()
    return low.endswith(".zip") and any(h.lower() in low for h in ZIP_HINTS)


def find_sources():
    """返回 (语料文件夹列表, 压缩包列表)"""
    dirs, zips = [], []
    for root in SEARCH_ROOTS:
        if not os.path.isdir(root):
            continue
        if looks_like_corpus(root):
            dirs.append(root)
        try:
            names = os.listdir(root)
        except Exception:
            continue
        for name in names:
            full = os.path.join(root, name)
            if os.path.isfile(full) and is_target_zip(name):
                zips.append(full)
            elif os.path.isdir(full):
                if looks_like_corpus(full):
                    dirs.append(full)
                # 再往里看一层（常见于 D:\古文语料\chinese-poetry.zip）
                try:
                    for n2 in os.listdir(full):
                        p2 = os.path.join(full, n2)
                        if os.path.isfile(p2) and is_target_zip(n2):
                            zips.append(p2)
                        elif os.path.isdir(p2) and looks_like_corpus(p2):
                            dirs.append(p2)
                except Exception:
                    pass
    return sorted(set(dirs)), sorted(set(zips))


# ============ 3. 从「文件夹」或「压缩包」里逐条读数据 ============
def iter_from_dir(root):
    """产出 (分组名, 文件名, 二进制内容)"""
    base = os.path.basename(root.rstrip("\\/"))
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if not fn.lower().endswith(".json"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            parts = rel.split(os.sep)
            group = parts[0] if len(parts) > 1 else base
            try:
                with open(full, "rb") as f:
                    yield group, fn, f.read()
            except Exception:
                continue


def iter_from_zip(zp):
    """直接读压缩包，不用解压"""
    with zipfile.ZipFile(zp) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".json")]
        # Gitee/GitHub 导出的包通常有一层统一的顶层目录，先判断出来
        tops = set()
        for n in names:
            parts = [p for p in n.split("/") if p]
            if len(parts) >= 2:
                tops.add(parts[0])
        strip_top = (len(tops) == 1)

        for name in sorted(names):
            parts = [p for p in name.split("/") if p]
            if any(p in SKIP_DIRS for p in parts):
                continue
            rest = parts[1:] if strip_top else parts
            if len(rest) < 2:
                continue          # 顶层散落的 json（README 之类）不是正文语料
            group = rest[0]
            if group in SKIP_DIRS:
                continue
            try:
                blob = z.read(name)
            except Exception:
                continue
            yield group, rest[-1], blob


def decode_json(blob):
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return json.loads(blob.decode(enc))
        except Exception:
            continue
    return None


# ============ 4. 把一条数据渲染成可读文本 ============
def render_item(item):
    if not isinstance(item, dict):
        return str(item).strip() + "\n\n"

    title = None
    for k in TITLE_KEYS:
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            title = v.strip()
            break

    author = None
    for k in AUTHOR_KEYS:
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            author = v.strip()
            break

    section_parts = []
    for k in SECTION_KEYS:
        v = item.get(k)
        if isinstance(v, str) and v.strip() and v.strip() not in (title, author):
            section_parts.append(v.strip())

    body = []
    for k in BODY_KEYS:
        v = item.get(k)
        if isinstance(v, list):
            body += [str(x).strip() for x in v if str(x).strip()]
        elif isinstance(v, str) and v.strip():
            body.append(v.strip())

    extra = []
    for k, v in item.items():
        if k in SKIP_KEYS or v is None:
            continue
        if isinstance(v, str) and v.strip():
            extra.append("%s: %s" % (k, v.strip()))
        elif isinstance(v, list) and v and all(isinstance(x, (str, int, float)) for x in v):
            extra.append("%s: %s" % (k, " ".join(str(x) for x in v)))

    lines = []
    head = []
    if title:
        head.append("《%s》" % title)
    elif section_parts:
        head.append("《%s》" % section_parts.pop(0))
    if author:
        head.append(author)
    if head:
        lines.append("  ".join(head))
    if section_parts:
        lines.append(" · ".join(section_parts))
    lines += body
    lines += extra

    if not lines:
        return ""
    return "\n".join(lines) + "\n\n"


# ============ 5. 一边读一边写（含自动分卷） ============
class GroupWriter:
    """同一类语料（如 全唐诗）写成一个或多个 txt，超过 MAX_BYTES 自动分卷"""

    def __init__(self, group):
        self.group = group
        self.idx = 1
        self.size = 0
        self.count = 0
        self.outputs = []
        self.fh = None
        self._open()

    def _open(self):
        if self.fh:
            self.fh.close()
        path = os.path.join(OUT_DIR, "%s_%02d.txt" % (self.group, self.idx))
        self.fh = open(path, "w", encoding="utf-8")
        self.outputs.append(path)
        self.idx += 1
        self.size = 0

    def write(self, txt):
        n = len(txt.encode("utf-8"))
        if self.size + n > MAX_BYTES:
            self._open()
        self.fh.write(txt)
        self.size += n
        self.count += 1

    def close(self):
        if self.fh:
            self.fh.close()
            self.fh = None
        self.outputs = [p for p in self.outputs if os.path.getsize(p) > 0]


# ============ 6. 主流程 ============
def main():
    print("=" * 58)
    print(" 古文语料转换工具：chinese-poetry JSON  →  Dify 可用 txt")
    print("=" * 58)

    dirs, zips = find_sources()

    if not dirs and not zips:
        print("\n[没找到语料]")
        print("我找过这些位置：")
        for r in SEARCH_ROOTS:
            print("   ", r)
        print("\n请确认：")
        print("   1) 你下载的 chinese-poetry 压缩包（或解压后的文件夹）在 D 盘")
        print("   2) 或者用记事本打开本文件，把你的实际路径加到第 21 行的 SEARCH_ROOTS 里")
        print("      例如：    r\"D:\\我的资料\\chinese-poetry-master.zip\",")
        return

    if zips:
        print("\n找到压缩包（不用解压，直接读）：")
        for z in zips:
            print("   -", z)
    if dirs:
        print("\n找到语料文件夹：")
        for d in dirs:
            print("   -", d)

    os.makedirs(OUT_DIR, exist_ok=True)
    print("\n输出目录：%s\n" % OUT_DIR)

    writers = {}

    def get_writer(g):
        if g not in writers:
            writers[g] = GroupWriter(g)
        return writers[g]

    def feed(source_iter, label):
        for group, fn, blob in source_iter:
            data = decode_json(blob)
            if data is None:
                continue
            items = data if isinstance(data, list) else [data]
            w = get_writer(group)
            for it in items:
                txt = render_item(it)
                if txt:
                    w.write(txt)

    for d in dirs:
        try:
            feed(iter_from_dir(d), d)
        except Exception as e:
            print("  [跳过] %s：%s" % (d, e))
    for z in zips:
        try:
            feed(iter_from_zip(z), z)
        except Exception as e:
            print("  [跳过] %s：%s" % (z, e))

    total = 0
    report = []
    for g in sorted(writers):
        w = writers[g]
        w.close()
        if w.count == 0:
            continue
        total += w.count
        print("[%s] %d 条  →  %d 个 txt" % (g, w.count, len(w.outputs)))
        report.append((g, w.count, w.outputs))

    rp = os.path.join(OUT_DIR, "转换报告.txt")
    with open(rp, "w", encoding="utf-8") as f:
        f.write("古文语料转换报告\n")
        f.write("=" * 42 + "\n")
        f.write("总计：%d 条语料\n" % total)
        f.write("输出目录：%s\n\n" % OUT_DIR)
        for g, c, outs in report:
            f.write("%s：%d 条\n" % (g, c))
            for p in outs:
                f.write("    %s  （%.1f MB）\n" % (os.path.basename(p), os.path.getsize(p) / 1024 / 1024))
            f.write("\n")

    print("\n" + "=" * 58)
    print("完成！共 %d 条语料，已输出到：%s" % (total, OUT_DIR))
    print("同目录的「转换报告.txt」里有每类的条数和文件体积。")
    print("=" * 58)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
    input("\n按回车键关闭窗口...")
