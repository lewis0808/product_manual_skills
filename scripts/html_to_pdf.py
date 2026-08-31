#!/usr/bin/env python3
"""用本机 Chrome / Edge 无头模式把 HTML 转成 PDF。

目录页码：如果 HTML 目录条目里带 <span class="toc-pageno"></span> 占位
（assets/manual-template.html 模板自带），脚本会先逐条探测对应章节的
实际页码、回填进 HTML，然后再输出 PDF。页码为 PDF 绝对页码（封面 = 第 1 页）。

用法:
    python html_to_pdf.py input.html [output.pdf]

依赖: 仅本机安装的 Chrome 或 Edge，无需任何第三方包。
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]

# 目录条目：<a href="#id">标题</a><span class="toc-pageno">…</span>（同一行 .t 内相邻）
TOC_ENTRY_RE = re.compile(
    r'<a\s+href="#([^"]+)"[^>]*>[^<]*</a>\s*<span\s+class="toc-pageno"',
    re.DOTALL,
)
TOC_PAGENO_RE = re.compile(r'(<span\s+class="toc-pageno"[^>]*>)[^<]*(</span>)')
# Chrome 生成的 PDF：页面对象是未压缩的 "/Type /Page"（排除 "/Type /Pages"）
PDF_PAGE_RE = re.compile(rb"/Type\s*/Page(?![/s])")

# 探测脚本：把目标元素之后的内容全部隐藏（hide_self 时连目标一起隐藏），
# 这样截短后 PDF 的页数就能推出目标元素在第几页。
PROBE_JS = """<script>
(function () {
  var el = document.getElementById(%(tid)s);
  if (!el) return;
  %(hide)s
  var node = el;
  while (node && node !== document.body) {
    var s = node.nextElementSibling;
    while (s) { s.style.display = "none"; s = s.nextElementSibling; }
    node = node.parentElement;
  }
})();
</script>"""


def find_browser() -> str:
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    sys.exit("错误：未找到 Chrome 或 Edge，请先安装其中一个浏览器。")


def run_chrome_print(browser: str, url: str, pdf: Path) -> None:
    """无头打印 url 为 pdf，等文件写完。失败时抛异常。"""
    # 每次用独立临时 profile，避免和正在运行的浏览器实例冲突
    with tempfile.TemporaryDirectory() as profile:
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--user-data-dir={profile}",
            "--no-pdf-header-footer",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={pdf}",
            "--virtual-time-budget=10000",
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    # 浏览器是异步写文件的，等文件出现且体积稳定
    for _ in range(50):
        if pdf.exists() and pdf.stat().st_size > 0:
            size1 = pdf.stat().st_size
            time.sleep(0.3)
            if pdf.exists() and pdf.stat().st_size == size1:
                return
        time.sleep(0.2)

    raise RuntimeError(f"打印失败：\n{result.stderr or result.stdout}")


def count_pdf_pages(pdf: Path) -> int:
    data = pdf.read_bytes()
    n = len(PDF_PAGE_RE.findall(data))
    if n == 0:  # 兜底：取页树 /Count 的最大值
        counts = re.findall(rb"/Count\s+(\d+)", data)
        n = max((int(c) for c in counts), default=0)
    return n


def probe_page(browser: str, html: Path, text: str, target_id: str,
               hide_self: bool, tmpdir: Path) -> int:
    """截短打印：返回"目标元素（含自身）不可见时"或"仅目标之后不可见时"的页数。"""
    js = PROBE_JS % {
        "tid": json.dumps(target_id),
        "hide": 'el.style.display = "none";' if hide_self else "",
    }
    if re.search(r"</body\s*>", text, re.IGNORECASE):
        probe_text = re.sub(r"</body\s*>", js + "\n</body>", text,
                            count=1, flags=re.IGNORECASE)
    else:
        probe_text = text + js
    # 临时 HTML 必须放在源文件同目录，截图等相对路径资源才能正常加载、分页才一致
    probe_html = html.with_name(f".{html.stem}.tocprobe.html")
    probe_pdf = tmpdir / "probe.pdf"
    try:
        probe_html.write_text(probe_text, encoding="utf-8")
        if probe_pdf.exists():
            probe_pdf.unlink()
        run_chrome_print(browser, probe_html.as_uri(), probe_pdf)
        return count_pdf_pages(probe_pdf)
    finally:
        probe_html.unlink(missing_ok=True)


def is_chapter(text: str, target_id: str) -> bool:
    """目标元素是否是另起一页的章节（section.chapter，带 page-break-before: always）。"""
    m = re.search(r'<\w+([^>]*?)\bid="%s"' % re.escape(target_id), text)
    if not m:
        return False
    cls = re.search(r'class="([^"]*)"', m.group(1))
    return bool(cls and "chapter" in cls.group(1).split())


def fill_toc_page_numbers(browser: str, html: Path, text: str, bom: bool) -> None:
    targets = TOC_ENTRY_RE.findall(text)
    spans = TOC_PAGENO_RE.findall(text)
    if not targets:
        return
    if len(targets) != len(spans):
        print(f"警告：目录条目（{len(targets)} 条）与 toc-pageno 占位"
              f"（{len(spans)} 个）数量不一致，跳过页码回填。", file=sys.stderr)
        return

    print(f"检测到 {len(targets)} 条目录，开始探测页码…")
    pages = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for tid in targets:
            if f'id="{tid}"' not in text:
                print(f'  警告：正文中找不到 id="{tid}"，该条页码留空。')
                pages.append("")
                continue
            # 章节必然另起一页：截掉自身及之后内容，页码 = 剩余页数 + 1；
            # 章节内小节（h3 等不会跨页）：只截掉之后的内容，页码 = 截短后页数。
            chapter = is_chapter(text, tid)
            n = probe_page(browser, html, text, tid, hide_self=chapter, tmpdir=tmpdir)
            page = n + 1 if chapter else n
            pages.append(str(page) if page > 0 else "")
            print(f"  #{tid} → 第 {page} 页" if page > 0 else f"  #{tid} → 探测失败，留空")

    it = iter(pages)
    new_text = TOC_PAGENO_RE.sub(lambda m: m.group(1) + next(it) + m.group(2), text)
    if new_text != text:
        html.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new_text.encode("utf-8"))
        print("目录页码已回填到 HTML。")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    html = Path(sys.argv[1]).resolve()
    if not html.is_file():
        sys.exit(f"错误：找不到文件 {html}")

    pdf = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else html.with_suffix(".pdf")
    pdf.parent.mkdir(parents=True, exist_ok=True)

    browser = find_browser()

    raw = html.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")

    try:
        fill_toc_page_numbers(browser, html, text, bom)
    except RuntimeError as e:
        print(f"警告：页码探测失败（{e}），直接按原样转 PDF。", file=sys.stderr)

    run_chrome_print(browser, html.as_uri(), pdf)
    print(f"PDF 已生成：{pdf}（{pdf.stat().st_size / 1024:.0f} KB，共 {count_pdf_pages(pdf)} 页）")


if __name__ == "__main__":
    main()
