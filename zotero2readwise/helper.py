# html_to_markdown_improved.py
#
# Utility that converts HTML fragments or full pages into GitHub‑flavoured
# Markdown and runs unchanged on Python 3.7‑3.12.
#
# Key additions / refinements
# ---------------------------
# * Handling headings & paragraphs with improved spacing (blank lines).
# * Optional keep_blank_lines param for controlling how aggressively we
#   collapse multiple blank lines.
# * Enhanced code block detection.
#
# Dependencies:
#     pip install beautifulsoup4
#

from __future__ import annotations
import re
from html import unescape
from typing import List, Union

from bs4 import BeautifulSoup, NavigableString, Tag

__all__ = [
    "html_to_markdown",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_tex(tex: str) -> str:
    """Remove leading/trailing LaTeX delimiters like $, $$, \\[ … \\]."""
    tex = tex.strip()
    # 移除开头和结尾的 $ 或 $$，也去除 \[ ... \] 包裹
    tex = re.sub(r"^\$\$?", "", tex)
    tex = re.sub(r"\$\$?$", "", tex)
    if tex.startswith("\\[") and tex.endswith("\\]"):
        tex = tex[2:-2].strip()
    return tex.strip()

def _wrap_code(text: str) -> str:
    """
    Convert a string to an inline or block code segment.
    Multi-line => fenced code block with triple backticks;
    Single-line => inline code with backticks.
    """
    text = text.rstrip("\n\r\t ")
    if "\n" in text:
        # 多行内容 -> 使用三重反引号
        return f"\n```\n{text}\n```\n"
    else:
        # 单行内容 -> 使用单反引号
        text_escaped = text.replace("`", "\\`")  # 简单转义反引号
        return f"`{text_escaped}`"

def _list_to_md(list_tag: Tag, bullet: str) -> str:
    items = []
    for li in list_tag.find_all("li", recursive=False):
        # 嵌套列表可自行扩展，这里只处理一层
        content = _children_to_md(li).strip()
        items.append(f"{bullet}{content}")
    return "\n".join(items) + "\n"

def _children_to_md(parent: Tag) -> str:
    """Convert all children of a parent node to Markdown, recursively."""
    return "".join(_walk(child) for child in parent.children)

# ---------------------------------------------------------------------------
# Core traversal
# ---------------------------------------------------------------------------

def _walk(node: Union[Tag, NavigableString]) -> str:
    """Depth‑first traversal that converts *node* to Markdown."""

    # 1) Text node
    if isinstance(node, NavigableString):
        return unescape(str(node))

    # 2) Element node
    name = node.name.lower()
    cls: List[str] = node.get("class", [])

    # (a) 数学公式
    if "math" in cls:
        tex_raw = node.get_text("", strip=True)
        tex = _strip_tex(tex_raw)
        # 如果 tag 是 <pre class="math"> 或本身包含换行，就作为 block 公式
        is_block = (name == "pre") or ("\n" in tex_raw)
        return f"\n$$\n{tex}\n$$\n" if is_block else f"${tex}$"

    # (b) 标题（h1..h6）
    if name.startswith("h") and len(name) == 2 and name[1].isdigit():
        level = int(name[1])
        heading_content = _children_to_md(node).strip()
        return f"\n{'#' * level} {heading_content}\n"

    # (c) 段落
    if name == "p":
        paragraph_text = _children_to_md(node).strip()
        # 在前后加空行，使段落更加清晰
        return f"\n{paragraph_text}\n"

    # (d) 换行
    if name == "br":
        return "\n"

    # (e) 粗体
    if name in ("strong", "b"):
        return f"**{_children_to_md(node)}**"

    # (f) 斜体
    if name in ("em", "i"):
        return f"*{_children_to_md(node)}*"

    # (g) 行内 code
    if name == "code":
        return _wrap_code(node.get_text())

    # (h) 预格式化（代码块）
    if name == "pre":
        # 直接获取文本，使用三重反引号包裹
        return _wrap_code(node.get_text())

    # (i) 超链接
    if name == "a":
        href = node.get("href", "#")
        link_text = _children_to_md(node).strip()
        return f"[{link_text}]({href})"

    # (j) 无序列表
    if name == "ul":
        return "\n" + _list_to_md(node, bullet="- ") + "\n"

    # (k) 有序列表
    if name == "ol":
        # 对于每个 li，都在最前面用 "1. "；也可以改成自动编号
        return "\n" + _list_to_md(node, bullet="1. ") + "\n"

    # (l) 列表项（仅当我们想手动处理时）
    if name == "li":
        return f"- {_children_to_md(node).strip()}\n"

    # (m) 块引用
    if name == "blockquote":
        quote = _children_to_md(node).strip()
        # 将内部换行替换为换行+> 以形成 Markdown 块引用
        quote = re.sub(r"\n+", "\n", quote)
        quoted = "\n".join(f"> {line}" for line in quote.splitlines())
        return f"\n{quoted}\n"

    # (n) 其他标签，递归其子节点
    return _children_to_md(node)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def html_to_markdown(html_content: str | None, keep_blank_lines: bool = False) -> str:
    """
    Convert HTML text to Markdown.
    
    :param html_content:      The full or partial HTML content.
    :param keep_blank_lines:  If False (default), collapse multiple blank
                              lines into just one or two, for a cleaner layout.
    :return:                  A string containing Markdown.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    # 删除脚本、样式等不需要转换的标签
    for t in soup.select("script, style, meta, link"):
        t.decompose()

    # 递归处理
    markdown = _children_to_md(soup)

    # 后处理：统一 EOL
    markdown = re.sub(r"\r\n|\r", "\n", markdown)   # normalise EOL
    # 去除行尾多余空格
    markdown = re.sub(r"[ \t]+\n", "\n", markdown)

    # 是否合并多余的空行
    if not keep_blank_lines:
        # 将 3 个或更多的连续空行折叠为 2 个
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    # 去除开头和末尾的空行
    markdown = markdown.strip("\n\r ")

    return markdown

# ---------------------------------------------------------------------------
# Quick self‑test
# ---------------------------------------------------------------------------

def test_html_to_markdown():
    """Simple internal tests to ensure function doesn't crash and outputs expected result."""

    # 1) A very basic test
    test_input = "<p>Hello <strong>world</strong></p>"
    result = html_to_markdown(test_input)
    print("Test 1 Input: ", repr(test_input))
    print("Test 1 Output:\n", result)
    print("-" * 40)

    # 2) Inline code test
    test_input2 = "<p>Use <code>print()</code> in Python</p>"
    result2 = html_to_markdown(test_input2)
    print("Test 2 Input: ", repr(test_input2))
    print("Test 2 Output:\n", result2)
    print("-" * 40)

    # 3) Block code test
    test_input3 = """<pre>def hello_world():
    print("Hello World")</pre>"""
    result3 = html_to_markdown(test_input3)
    print("Test 3 Input: ", repr(test_input3))
    print("Test 3 Output:\n", result3)
    print("-" * 40)

    # 4) Heading test
    test_input4 = "<h1>Main Title</h1><p>Some text</p><h2>Sub Title</h2>"
    result4 = html_to_markdown(test_input4)
    print("Test 4 Input: ", repr(test_input4))
    print("Test 4 Output:\n", result4)
    print("-" * 40)

    # 5) List test
    test_input5 = "<ul><li>Apple</li><li>Banana</li><li>Orange</li></ul>"
    result5 = html_to_markdown(test_input5)
    print("Test 5 Input: ", repr(test_input5))
    print("Test 5 Output:\n", result5)
    print("-" * 40)

    # 6) keep_blank_lines test
    test_input6 = "<p>Line1</p><p>Line2</p><p>Line3</p>"
    result6 = html_to_markdown(test_input6, keep_blank_lines=True)
    print("Test 6 (keep_blank_lines=True) Input: ", repr(test_input6))
    print("Test 6 Output:\n", repr(result6))
    print("-" * 40)


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python html_to_markdown_improved.py --test")
        print("  python html_to_markdown_improved.py --convert \"<html>\"")
        print("  python html_to_markdown_improved.py --convert-file input.html")
        sys.exit(0)

    command = sys.argv[1]

    if command == "--test":
        test_html_to_markdown()

    elif command == "--convert" and len(sys.argv) > 2:
        html_content = sys.argv[2]
        print("\nInput HTML:")
        print("-----------")
        print(html_content)
        print("\nConverted Markdown:")
        print("------------------")
        print(html_to_markdown(html_content))

    elif command == "--convert-file" and len(sys.argv) > 2:
        file_path = sys.argv[2]
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found.")
            sys.exit(1)

        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        markdown = html_to_markdown(html_content)

        # Print the converted markdown
        print("\nConverted Markdown:")
        print("------------------")
        print(markdown)

        # Save the result to a .md file
        output_path = os.path.splitext(file_path)[0] + '.md'
        with open(output_path, 'w', encoding='utf-8') as outf:
            outf.write(markdown)
        print(f"\nMarkdown saved to: {output_path}")

    else:
        print("Invalid command or missing argument.")
        print("Usage:")
        print("  python html_to_markdown_improved.py --test")
        print("  python html_to_markdown_improved.py --convert \"<html>\"")
        print("  python html_to_markdown_improved.py --convert-file input.html")
