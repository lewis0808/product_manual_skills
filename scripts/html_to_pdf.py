#!/usr/bin/env python3
"""用本机 Chrome / Edge 无头模式把 HTML 转成 PDF。

用法:
    python html_to_pdf.py input.html [output.pdf]

依赖: 仅本机安装的 Chrome 或 Edge，无需任何第三方包。
"""
import os
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


def find_browser() -> str:
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    sys.exit("错误：未找到 Chrome 或 Edge，请先安装其中一个浏览器。")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    html = Path(sys.argv[1]).resolve()
    if not html.is_file():
        sys.exit(f"错误：找不到文件 {html}")

    pdf = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else html.with_suffix(".pdf")
    pdf.parent.mkdir(parents=True, exist_ok=True)

    browser = find_browser()
    url = html.as_uri()

    # 打印的 PDF 会写到 --print-to-pdf 指定的路径。
    # 用独立临时 profile，避免和正在运行的浏览器实例冲突。
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
                break
        time.sleep(0.2)

    if not pdf.exists() or pdf.stat().st_size == 0:
        sys.exit(f"转换失败：\n{result.stderr or result.stdout}")

    print(f"PDF 已生成：{pdf}（{pdf.stat().st_size / 1024:.0f} KB）")


if __name__ == "__main__":
    main()
