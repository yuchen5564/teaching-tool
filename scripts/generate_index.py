#!/usr/bin/env python3
"""
掃描 repo 中的靜態 HTML 頁面，在 index.html 生成連結清單。

行為：
- 若 index.html 已存在且含有標記
      <!-- AUTO-LINKS:START -->
      <!-- AUTO-LINKS:END -->
  只替換兩個標記之間的內容（其餘版面由你自己設計）。
- 若 index.html 不存在或沒有標記，產生一個完整的預設頁面。

用法：python3 scripts/generate_index.py [repo根目錄]
"""
import html
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
INDEX = ROOT / "index.html"

START = "<!-- AUTO-LINKS:START -->"
END = "<!-- AUTO-LINKS:END -->"

# 不掃描的資料夾
EXCLUDE_DIRS = {".git", ".github", "node_modules", "vendor", "_site", ".venv", "venv", "scripts"}
# 不列出的檔名
EXCLUDE_FILES = {"404.html"}
# 也可在檔案 <head> 內加 <meta name="auto-index" content="skip"> 讓它不被列出

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
DESC_RE = re.compile(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', re.I | re.S)
SKIP_RE = re.compile(r'<meta\s+name=["\']auto-index["\']\s+content=["\']skip["\']', re.I)


def read_text(p: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "big5", "latin-1"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return ""


def collect_pages():
    pages = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if not name.lower().endswith((".html", ".htm")) or name in EXCLUDE_FILES:
                continue
            path = Path(dirpath) / name
            rel = path.relative_to(ROOT).as_posix()
            if rel == "index.html":  # 根目錄的 index 自己不列
                continue
            text = read_text(path)
            if SKIP_RE.search(text):
                continue
            m = TITLE_RE.search(text)
            title = html.unescape(re.sub(r"\s+", " ", m.group(1)).strip()) if m else ""
            d = DESC_RE.search(text)
            desc = html.unescape(d.group(1).strip()) if d else ""
            # 子資料夾的 index.html 連到資料夾本身
            href = rel[: -len("index.html")] if name == "index.html" else rel
            folder = str(Path(rel).parent) if Path(rel).parent != Path(".") else ""
            if name == "index.html":
                folder = str(Path(rel).parent.parent) if Path(rel).parent.parent != Path(".") else ""
            pages.append({
                "href": href,
                "title": title or Path(rel).stem if name != "index.html" else (title or Path(rel).parent.name),
                "desc": desc,
                "folder": folder,
            })
    return pages


def render_links(pages) -> str:
    if not pages:
        return "<p>目前沒有其他頁面。</p>"
    groups = defaultdict(list)
    for p in pages:
        groups[p["folder"]].append(p)
    out = []
    for folder in sorted(groups, key=lambda f: (f != "", f)):
        if folder:
            out.append(f'<h2>{html.escape(folder)}/</h2>')
        out.append('<ul class="auto-links">')
        for p in sorted(groups[folder], key=lambda x: x["title"].lower()):
            line = f'  <li><a href="{html.escape(p["href"])}">{html.escape(p["title"])}</a>'
            line += f' <code>{html.escape(p["href"])}</code>'
            if p["desc"]:
                line += f'<br><small>{html.escape(p["desc"])}</small>'
            out.append(line + "</li>")
        out.append("</ul>")
    return "\n".join(out)


DEFAULT_TEMPLATE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: system-ui, "Noto Sans TC", sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 16px; line-height: 1.6; color: #222; }}
  h1 {{ border-bottom: 2px solid #eee; padding-bottom: .4rem; }}
  h2 {{ font-size: 1.05rem; color: #666; margin-top: 1.6rem; }}
  ul.auto-links {{ list-style: none; padding: 0; }}
  ul.auto-links li {{ padding: .5rem 0; border-bottom: 1px solid #f0f0f0; }}
  ul.auto-links a {{ font-weight: 600; text-decoration: none; color: #0969da; }}
  ul.auto-links code {{ color: #999; font-size: .8rem; margin-left: .5rem; }}
  small {{ color: #555; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #0d1117; color: #e6edf3; }}
    h1 {{ border-color: #30363d; }}
    ul.auto-links li {{ border-color: #21262d; }}
    ul.auto-links a {{ color: #58a6ff; }}
    small {{ color: #9da7b3; }}
  }}
</style>
</head>
<body>
<h1>{title}</h1>
{start}
{links}
{end}
</body>
</html>
"""


def main():
    pages = collect_pages()
    links = render_links(pages)
    if INDEX.exists():
        content = read_text(INDEX)
        if START in content and END in content:
            new = re.sub(
                re.escape(START) + r".*?" + re.escape(END),
                lambda _: f"{START}\n{links}\n{END}",
                content,
                flags=re.S,
            )
            INDEX.write_text(new, encoding="utf-8")
            print(f"已更新 index.html 標記區塊，共 {len(pages)} 個頁面")
            return
        print("index.html 沒有 AUTO-LINKS 標記，將以預設樣板覆寫")
    title = ROOT.name or "Pages"
    INDEX.write_text(
        DEFAULT_TEMPLATE.format(title=html.escape(title), start=START, links=links, end=END),
        encoding="utf-8",
    )
    print(f"已產生 index.html，共 {len(pages)} 個頁面")


if __name__ == "__main__":
    main()
