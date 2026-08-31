# product-manual 使用说明书生成 Skill

为一个已有的 Web 平台或 Windows 桌面软件（exe）生成**用户使用说明书**：读代码 + 查看实际界面并截图 → 产出单文件 HTML（可直接修改）→ 按需转 PDF（自动回填目录页码）。

## 目录结构

```
product-manual/
├── SKILL.md                    # Skill 定义：工作流程、省 token 规则（AI 读取）
├── assets/
│   ├── manual-template.html    # 说明书模板（封面/修订记录/目录/章节/FAQ，打印友好）
│   └── logo.png                # 公司 logo，封面引用
└── scripts/
    ├── html_to_pdf.py          # HTML → PDF（本机 Chrome/Edge 无头打印，零依赖；自动回填目录页码）
    ├── screenshot.mjs          # 网页自动截图（puppeteer-core + 本机 Chrome/Edge）
    ├── screenshot_window.ps1   # exe 桌面软件截图（截前台窗口/全屏，Windows 自带 PowerShell）
    └── node_modules/           # screenshot.mjs 的依赖（已安装，勿删）
```

## 如何使用

把 `product-manual/` 作为项目级 skill 放到项目的 skills 目录下（或当前工作目录）。之后直接对 AI 说：

> 给 XX 系统生成使用说明书，访问地址是 https://xxx
> 给 XX 软件生成使用说明书，是个 exe 桌面程序

AI 会自动按 SKILL.md 的流程执行：

1. **收集信息**：读项目代码整理功能模块清单（Web 读路由/菜单，exe 读窗体/界面定义），只问你代码里挖不到的信息
2. **看实际界面 + 截图**：菜单文案、按钮名以实际界面为准
   - Web：用 `screenshot.mjs` 逐页截图；需要登录的系统会弹出真实浏览器让你**手动登录一次**，登录态保存后所有内页自动截
   - exe：AI 无法替你操作软件，用 `screenshot_window.ps1` 逐个界面截图——AI 运行截图命令后，你在倒计时内把软件窗口切到前台即可
3. **生成 HTML**：基于模板填充内容，截图直接复用进说明书，输出到产品目录（如 `docs/user-manual.html`）
4. **转 PDF 前会询问**：你一般还要修改 HTML，可选择让 AI 立即转，或改完后自己跑脚本

## 脚本单独使用

### 网页截图

```bash
cd product-manual/scripts

# 公开页面
node screenshot.mjs <url> out.png --width 1440 --height 900 --full

# 需要登录的页面：第一步手动登录存登录态（弹出浏览器，登录后回终端按回车）
node screenshot.mjs <登录页url> --save-auth auth.json

# 第二步带登录态无头截图
node screenshot.mjs <内页url> out.png --auth auth.json --full

# 批量：tasks.txt 每行 "url 输出路径"
node screenshot.mjs --batch tasks.txt --auth auth.json
```

### HTML 转 PDF

```bash
python product-manual/scripts/html_to_pdf.py 说明书.html            # 输出同名 .pdf
python product-manual/scripts/html_to_pdf.py 说明书.html out/a.pdf  # 指定输出路径
```

> 注意：**转 PDF 统一用脚本，不要用浏览器 Ctrl+P**——浏览器打印会自带页眉页脚（URL 和日期），脚本已去除。脚本还会自动探测目录各章节页码并回填。

### exe 桌面软件截图（仅 Windows）

```bash
# 倒计时 5 秒后截取前台窗口（执行后把软件目标窗口切到前台）
powershell -ExecutionPolicy Bypass -File product-manual/scripts/screenshot_window.ps1 out.png

# 自定义倒计时 / 截全屏（菜单展开、多窗口同屏等场景）
powershell -ExecutionPolicy Bypass -File product-manual/scripts/screenshot_window.ps1 out.png -Delay 8
powershell -ExecutionPolicy Bypass -File product-manual/scripts/screenshot_window.ps1 out.png -Full
```

## 环境要求

- 本机安装 Chrome 或 Edge（网页截图和转 PDF 都靠它，自动查找）
- Python 3（转 PDF 用）
- Node.js（网页截图用；`scripts/node_modules` 已含 puppeteer-core，换机器需重装：`cd scripts && npm install`）
- Windows PowerShell（exe 桌面软件截图用，系统自带）

## 模板说明

模板按《用户操作手册写法》规范设计，包含：封面 → 修订记录 → 目录 → 阅读约定与名词解释 → 产品概述 → 快速上手 → 按"角色 + 端"划分的功能章节 → 常见问题 → 附录。

使用约定：

- 按钮统一写【按钮】，系统提示统一写"提示语"，截图上的标注用 ①②③ 与步骤对应
- 同一功能的多步操作建议拼成一张竖向**长图**（圈出按钮位置），对应步骤列表
- 修订记录每次更新必须登记，手册版本与系统版本对应
- 目录条目里的 `<span class="toc-pageno">` 占位不要删：`html_to_pdf.py` 转 PDF 时会自动探测各章节实际页码并回填（PDF 绝对页码，封面 = 第 1 页）
- 复制模板时把 `logo.png` 一并复制到说明书同目录（封面按相对路径引用）
