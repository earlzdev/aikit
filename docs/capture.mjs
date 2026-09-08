// Renders a capture page to a PNG frame sequence with headless Chrome over the
// DevTools Protocol. No npm install: Node's built-in WebSocket speaks CDP
// directly, and the only other requirement is a Chrome on the box.
//
// Deterministic on purpose — the page exposes __frames and __frame(n), so this
// draws frame n and screenshots it rather than screen-recording a clock and
// hoping the timing lands.
//
// The page is an argument because there is more than one of them, and a
// hardcoded path meant the README could tell you to regenerate one animation
// with a command that quietly rebuilt the other.
//
//   node docs/capture.mjs dark out/frames [docs/pipeline-capture.html]
//   node docs/capture.mjs dark out/frames docs/steploop-capture.html
//   ffmpeg -framerate 12 -i out/frames/%04d.png ... pipeline.gif
import { spawn } from "node:child_process";
import { mkdir, writeFile, rm } from "node:fs/promises";
import { setTimeout as sleep } from "node:timers/promises";
import path from "node:path";
import { existsSync } from "node:fs";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9333, SCALE = 2, W = 900, H = 620;
const theme = process.argv[2] ?? "dark";
const outDir = path.resolve(process.argv[3] ?? "out/frames");
const src = process.argv[4] ?? "docs/pipeline-capture.html";
if (!existsSync(src)) { console.error(`no such capture page: ${src}`); process.exit(2); }
const page = "file://" + path.resolve(src) + "?theme=" + theme;

const profile = path.join(process.env.TMPDIR ?? "/tmp", `aikit-capture-${theme}`);
await rm(profile, { recursive: true, force: true });
await rm(outDir, { recursive: true, force: true });
await mkdir(outDir, { recursive: true });

const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${PORT}`, "--remote-allow-origins=*",
  `--user-data-dir=${profile}`, "--no-first-run", "--no-default-browser-check",
  "--hide-scrollbars", "--disable-gpu", `--window-size=${W},${H}`, page,
], { stdio: "ignore" });

// Chrome writes the port file before the socket answers; poll rather than sleep.
let targets = null;
for (let i = 0; i < 60 && !targets; i++) {
  try {
    const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
    targets = list.find(t => t.type === "page" && t.webSocketDebuggerUrl);
  } catch { await sleep(250); }
}
if (!targets) { chrome.kill(); throw new Error("headless Chrome never answered on CDP"); }

const ws = new WebSocket(targets.webSocketDebuggerUrl);
await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = no; });

let id = 0;
const pending = new Map();
ws.onmessage = e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
};
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const n = ++id;
  pending.set(n, m => m.error ? reject(new Error(method + ": " + m.error.message)) : resolve(m.result));
  ws.send(JSON.stringify({ id: n, method, params }));
});
const evaluate = async expression => {
  const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text);
  return r.result.value;
};

await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride",
  { width: W, height: H, deviceScaleFactor: SCALE, mobile: false });

// Webfonts arrive over the network; a frame captured before they land renders
// in the fallback stack and the whole sequence jumps when they arrive.
for (let i = 0; i < 40; i++) {
  if (await evaluate("document.fonts && document.fonts.status === 'loaded'")) break;
  await sleep(250);
}
await evaluate("document.fonts.ready.then(()=>true)");
await sleep(400);

const total = await evaluate("window.__frames");
if (!total) throw new Error("the page never defined __frames");
process.stdout.write(`${theme}: ${total} frames → ${outDir}\n`);

for (let n = 0; n < total; n++) {
  await evaluate(`window.__frame(${n}), true`);
  const { data } = await send("Page.captureScreenshot", {
    format: "png", captureBeyondViewport: false,
    clip: { x: 0, y: 0, width: W, height: H, scale: SCALE },
  });
  await writeFile(path.join(outDir, String(n).padStart(4, "0") + ".png"), Buffer.from(data, "base64"));
  if (n % 25 === 0) process.stdout.write(`  ${n}/${total}\n`);
}

ws.close();
chrome.kill();
// Chrome keeps flushing its profile after the kill, so a straight rm races it
// and throws ENOTEMPTY on a run that in fact succeeded. Retry, then shrug.
for (let i = 0; i < 5; i++) {
  try { await rm(profile, { recursive: true, force: true }); break; } catch { await sleep(400); }
}
process.stdout.write(`${theme}: done\n`);
