#!/usr/bin/env node
/**
 * 网页自动截图脚本（puppeteer-core + 本机 Chrome/Edge，无需下载浏览器）。
 *
 * 用法:
 *   node screenshot.mjs <url> <输出.png> [选项]
 *
 * 选项:
 *   --width 1440          视口宽度
 *   --height 900          视口高度
 *   --full                整页截图（默认只截视口）
 *   --wait "选择器"        等待某元素出现再截（如 ".app-main"）
 *   --delay 1000          额外等待毫秒数
 *   --auth storage.json   登录态文件（localStorage/cookies，见下方说明）
 *   --save-auth out.json  打开有头浏览器让你手动登录，登录后回车保存登录态
 *
 * 需要登录的页面标准流程（两步）:
 *   1. node screenshot.mjs <登录页url> --save-auth auth.json
 *      → 弹出真实浏览器，手动登录，回终端按回车，登录态存入 auth.json
 *   2. node screenshot.mjs <内页url> out.png --auth auth.json --full
 *      → 带登录态无头截图
 *
 * 批量: 每行一个 "url 输出路径" 写进 tasks.txt，然后:
 *   node screenshot.mjs --batch tasks.txt --auth auth.json
 */
import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import puppeteer from "puppeteer-core";

const BROWSERS = [
  String.raw`C:\Program Files\Google\Chrome\Application\chrome.exe`,
  String.raw`C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`,
  String.raw`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`,
  String.raw`C:\Program Files\Microsoft\Edge\Application\msedge.exe`,
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
];

function findBrowser() {
  const p = BROWSERS.find((b) => fs.existsSync(b));
  if (!p) {
    console.error("错误：未找到 Chrome 或 Edge。");
    process.exit(1);
  }
  return p;
}

function parseArgs(argv) {
  const opt = {
    width: 1440, height: 900, full: false,
    wait: null, delay: 0, auth: null, saveAuth: null, batch: null,
    positional: [],
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--full") opt.full = true;
    else if (a === "--width") opt.width = +argv[++i];
    else if (a === "--height") opt.height = +argv[++i];
    else if (a === "--wait") opt.wait = argv[++i];
    else if (a === "--delay") opt.delay = +argv[++i];
    else if (a === "--auth") opt.auth = argv[++i];
    else if (a === "--save-auth") opt.saveAuth = argv[++i];
    else if (a === "--batch") opt.batch = argv[++i];
    else opt.positional.push(a);
  }
  return opt;
}

/** 把登录态（localStorage + cookies）注入页面 */
async function applyAuth(page, authFile, url) {
  const auth = JSON.parse(fs.readFileSync(authFile, "utf8"));
  if (auth.cookies?.length) await page.setCookie(...auth.cookies);
  if (auth.localStorage && Object.keys(auth.localStorage).length) {
    // 先打开同域页面，才能写 localStorage
    await page.goto(new URL(url).origin, { waitUntil: "domcontentloaded" });
    await page.evaluate((kv) => {
      for (const [k, v] of Object.entries(kv)) localStorage.setItem(k, v);
    }, auth.localStorage);
  }
}

async function dumpAuth(page, file) {
  const cookies = await page.cookies();
  const localStorage = await page.evaluate(() => ({ ...window.localStorage }));
  fs.writeFileSync(file, JSON.stringify({ cookies, localStorage }, null, 2));
  console.log(`登录态已保存：${file}`);
}

async function shoot(page, url, out, opt) {
  await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 });
  if (opt.wait) await page.waitForSelector(opt.wait, { timeout: 30000 });
  if (opt.delay) await new Promise((r) => setTimeout(r, opt.delay));
  fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
  await page.screenshot({ path: out, fullPage: opt.full });
  console.log(`截图已保存：${out}`);
}

async function main() {
  const opt = parseArgs(process.argv.slice(2));
  const browser = await puppeteer.launch({
    executablePath: findBrowser(),
    headless: !opt.saveAuth, // 手动登录模式需要有头浏览器
    args: ["--no-sandbox", "--disable-gpu"],
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: opt.width, height: opt.height });

    // 模式1：手动登录并保存登录态
    if (opt.saveAuth) {
      const url = opt.positional[0];
      if (!url) throw new Error("--save-auth 需要提供登录页 URL");
      await page.goto(url, { waitUntil: "domcontentloaded" });
      console.log("请在打开的浏览器中完成登录，登录成功后回到这里按回车…");
      await new Promise((r) => readline.createInterface({ input: process.stdin, output: process.stdout }).question("", r));
      await dumpAuth(page, opt.saveAuth);
      return;
    }

    // 模式2：批量
    if (opt.batch) {
      const lines = fs.readFileSync(opt.batch, "utf8").split("\n")
        .map((l) => l.trim()).filter((l) => l && !l.startsWith("#"));
      for (const line of lines) {
        const [url, out] = line.split(/\s+/);
        const fresh = await browser.newPage();
        await fresh.setViewport({ width: opt.width, height: opt.height });
        if (opt.auth) await applyAuth(fresh, opt.auth, url);
        await shoot(fresh, url, out, opt);
        await fresh.close();
      }
      return;
    }

    // 模式3：单张
    const [url, out] = opt.positional;
    if (!url || !out) throw new Error("用法: node screenshot.mjs <url> <输出.png> [选项]");
    if (opt.auth) await applyAuth(page, opt.auth, url);
    await shoot(page, url, out, opt);
  } finally {
    await browser.close();
  }
}

main().catch((e) => { console.error(`失败：${e.message}`); process.exit(1); });
