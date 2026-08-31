---
name: product-manual
description: 为用户已写好的 Web 平台/产品生成用户使用说明书。会访问线上网址实际查看页面并自动截图，产出单文件 HTML（内嵌样式、可直接修改、打印友好），并可选用本机 Chrome/Edge 无头模式转成 PDF。当用户要求"生成使用说明书/用户手册/帮助文档"，或提到 product-manual、manual-template、html_to_pdf、screenshot 时使用。
---

# 产品使用说明书生成流程

目标：为一个已有的 Web 平台生成用户说明书，**省 token**，产出易修改的 HTML，最后按需转 PDF。

## 省 token 铁律

- **绝不在对话里粘贴 HTML 全文**。所有内容直接写入文件；修改时用 Edit 做精准局部替换，不要重写整个文件。
- 样式骨架不要每次现写：直接复制 `assets/manual-template.html` 作为起点，只生成/替换内容区。
- 产品信息优先自己从代码里挖（README、路由、菜单、页面组件、package.json），再结合线上页面截图核对，只问用户代码和网页里都拿不到的东西。
- 截图用脚本生成图片文件，HTML 里用 `<img src="相对路径">` 引用，**不要 base64 内嵌**；截图文件直接复用进说明书，一图两用。
- 看截图用 ReadMediaFile，一次并行读多张，不要反复重读同一张。
- 需要用户确认时一次问完，不要逐条来回。

## 工作流程

### 1. 收集信息（代码 + 线上页面，两条腿走）

先读项目：README、路由定义、侧边栏/导航组件、主要页面。据此整理出功能模块清单和页面 URL 清单。

然后**实际访问线上网址看页面效果**——不只看代码。用截图脚本逐页截图，再用 ReadMediaFile 查看截图，确认每个页面真实长什么样（菜单文案、按钮、表格列名以线上为准，代码可能过时）。脚本用法见文末「脚本」一节：

- 公开页面：直接截图
- **需要登录的页面**（两步）：先 `--save-auth` 弹出真实浏览器让用户手动登录、保存登录态到 `auth.json`；之后所有内页带 `--auth auth.json` 无头截图，无需用户再参与
- 多页面：用 `--batch` 一次截完

截图统一存到说明书旁的 `assets/screenshots/` 目录，命名用语义化英文（如 `dashboard.png`、`user-list.png`），后面写 HTML 时直接引用。

代码里挖不到、截图也看不出的信息（产品定位、权限规则、业务约定）再问用户，用 AskUserQuestion 一次性合并提问，通常只有：
- 产品名称、面向的用户角色（管理员/普通用户…）
- 平台访问地址、是否需要登录截图
- 说明书语言（默认中文）

### 2. 生成 HTML

- 输出路径默认 `<产品目录>/docs/user-manual.html`，或用户指定位置。
- 复制 `assets/manual-template.html` 为起点，同时把 `assets/logo.png` 复制到说明书 HTML 同目录（封面引用的是 `logo.png` 相对路径；若放别处需改 src）。用 Edit 逐个章节填入真实内容。模板结构：封面 → 修订记录 → 目录 → 阅读约定与名词解释 → 产品概述 → 快速上手 → 各端/功能章节 → FAQ → 附录。
- 目录条目保留 `<span class="toc-pageno"></span>` 占位（留空即可），转 PDF 时脚本自动回填页码；新增/删除目录条目时按模板同款格式写 `<span class="t"><a href="#id">标题</a><span class="toc-pageno"></span></span>`。
- 内容面向最终用户，写"点哪里、看到什么、注意什么"，不写实现细节。界面上的菜单名、按钮名、表格列名以线上截图看到的为准。
- 把第 1 步截好的截图直接引用进来（相对路径 `assets/screenshots/xxx.png`），替换模板里的 `screenshot-placeholder` 占位块；页面上需要演示但没截到的操作，补截或保留占位符让用户自行替换。
- 生成完只告诉用户文件路径和章节清单，不贴代码。

### 3. 转 PDF —— 必须询问，不要自作主张

HTML 生成后，问用户：

> 说明书 HTML 已生成，你可能还要修改。要我现在转成 PDF，还是你改完后自己跑脚本？

- 用户让自己跑：给出命令 `python <skill目录>/scripts/html_to_pdf.py <html路径> [输出pdf路径]`，结束。
- 用户让现在转：直接运行该脚本，报告 PDF 路径。
- 用户改完 HTML 后再来转：同样跑脚本即可，脚本可重复执行。
- **转 PDF 统一用脚本，不要在浏览器里 Ctrl+P 打印**——浏览器打印会带上页眉页脚（URL 和日期），脚本已用 `--no-pdf-header-footer` 去除。

## 脚本

`scripts/html_to_pdf.py` — 自动查找本机 Chrome 或 Edge，无头模式打印为 PDF（A4、含背景色、无边距问题已处理）。**转 PDF 时会自动探测目录各章节的实际页码并回填进 HTML**（依赖模板目录里的 `<span class="toc-pageno">` 占位，生成/修改 HTML 时不要删掉它；页码为 PDF 绝对页码，封面 = 第 1 页）。用法：

```bash
python scripts/html_to_pdf.py manual.html            # 输出 manual.pdf
python scripts/html_to_pdf.py manual.html out/a.pdf  # 指定输出
```

依赖：仅本机 Chrome/Edge，无需安装任何包。

`scripts/screenshot.mjs` — 网页自动截图（puppeteer-core + 本机 Chrome/Edge，依赖已装在 `scripts/node_modules`，无需下载浏览器）。用法：

```bash
# 公开页面
node scripts/screenshot.mjs <url> out.png [--width 1440] [--height 900] [--full] [--wait "选择器"] [--delay 毫秒]

# 需要登录的页面：第一步手动登录存登录态（弹出浏览器，登录后回终端按回车）
node scripts/screenshot.mjs <登录页url> --save-auth auth.json
# 第二步带登录态无头截图
node scripts/screenshot.mjs <内页url> out.png --auth auth.json --full

# 批量：tasks.txt 每行 "url 输出路径"
node scripts/screenshot.mjs --batch tasks.txt --auth auth.json
```
