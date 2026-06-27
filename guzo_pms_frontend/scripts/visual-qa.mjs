import { spawn } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { setTimeout as delay } from "node:timers/promises";

const EDGE_PATH =
  process.env.QA_EDGE_PATH ||
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const BASE_URL = process.env.QA_BASE_URL || "http://127.0.0.1:8000";
const DEBUG_PORT = Number(
  process.env.QA_DEBUG_PORT || 9300 + Math.floor(Math.random() * 500)
);
const OUT_DIR = resolve("screenshots", "responsive-qa");
const COMMAND_TIMEOUT_MS = Number(process.env.QA_COMMAND_TIMEOUT_MS || 8000);
const ROUTE_TIMEOUT_MS = Number(process.env.QA_ROUTE_TIMEOUT_MS || 25000);
const ROUTE_FILTER = process.env.QA_ROUTE_FILTER
  ? new RegExp(process.env.QA_ROUTE_FILTER)
  : null;

const APP_URL = new URL(BASE_URL);
const REPORT_FILE = join(OUT_DIR, "responsive-qa-results.json");

const viewports = [
  ["desktop", 1440, 900],
  ["tablet", 768, 1024],
  ["mobile", 390, 844],
];

const routes = [
  ["login", "/login", "Login", false],
  ["dashboard", "/dashboard", "Dashboard", true],
  ["frontdesk", "/frontdesk", "Front Desk", true],
  ["reservations", "/reservations", "Reservations", true],
  ["housekeeping", "/housekeeping", "Housekeeping", true],
  ["finance", "/finance", "Finance", true],
].filter(([routeName]) => !ROUTE_FILTER || ROUTE_FILTER.test(routeName));

const adminSession = {
  username: "responsive.qa@guzo.local",
  email: "responsive.qa@guzo.local",
  full_name: "Responsive QA",
  role: "admin",
  department: "it_admin",
  property_code: "DRE001",
  property_codes: ["DRE001", "NN002"],
};

function withTimeout(promise, timeoutMs, label) {
  let timeoutId;
  const timeout = new Promise((_, reject) => {
    timeoutId = setTimeout(
      () => reject(new Error(`${label} timed out after ${timeoutMs}ms`)),
      timeoutMs
    );
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timeoutId));
}

function cdpSocket(url) {
  const ws = new WebSocket(url);
  let nextId = 1;
  const pending = new Map();
  const listeners = new Map();

  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) {
      const callbacks = listeners.get(message.method) || [];
      callbacks.forEach((callback) => callback(message));
      return;
    }

    const { resolve, reject, timeoutId } = pending.get(message.id);
    pending.delete(message.id);
    clearTimeout(timeoutId);

    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result || {});
  });

  function send(method, params = {}, sessionId, timeoutMs = COMMAND_TIMEOUT_MS) {
    const id = nextId;
    nextId += 1;

    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`${method} timed out after ${timeoutMs}ms`));
      }, timeoutMs);

      pending.set(id, { resolve, reject, timeoutId });
      ws.send(JSON.stringify(payload));
    });
  }

  function on(method, callback) {
    const callbacks = listeners.get(method) || [];
    callbacks.push(callback);
    listeners.set(method, callbacks);
    return () => {
      const nextCallbacks = (listeners.get(method) || []).filter((item) => item !== callback);
      listeners.set(method, nextCallbacks);
    };
  }

  return new Promise((resolve, reject) => {
    ws.addEventListener("open", () =>
      resolve({
        send,
        on,
        close: () => ws.close(),
      })
    );
    ws.addEventListener("error", reject);
  });
}

async function waitForDebugger() {
  for (let i = 0; i < 60; i += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/version`);
      if (response.ok) return response.json();
    } catch {
      await delay(250);
    }
  }
  throw new Error("Edge remote debugging endpoint did not start.");
}

async function isAppReachable() {
  try {
    const response = await fetch(BASE_URL);
    return response.ok || response.status < 500;
  } catch {
    return false;
  }
}

async function cdpTargetSession(client, targetId) {
  const attached = await client.send("Target.attachToTarget", {
    targetId,
    flatten: false,
  });
  const sessionId = attached.sessionId;
  let nextId = 1;
  const pending = new Map();

  const unsubscribe = client.on("Target.receivedMessageFromTarget", (event) => {
    if (event.params?.sessionId !== sessionId) return;

    const message = JSON.parse(event.params.message);
    if (!message.id || !pending.has(message.id)) return;

    const { resolve, reject, timeoutId } = pending.get(message.id);
    pending.delete(message.id);
    clearTimeout(timeoutId);

    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result || {});
  });

  function send(method, params = {}, unusedSessionId, timeoutMs = COMMAND_TIMEOUT_MS) {
    const id = nextId;
    nextId += 1;
    const message = JSON.stringify({ id, method, params });

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`${method} timed out after ${timeoutMs}ms`));
      }, timeoutMs);

      pending.set(id, { resolve, reject, timeoutId });
      client
        .send("Target.sendMessageToTarget", { sessionId, message }, undefined, timeoutMs)
        .catch((error) => {
          pending.delete(id);
          clearTimeout(timeoutId);
          reject(error);
        });
    });
  }

  return {
    send,
    close: () => {
      unsubscribe();
      return client
        .send("Target.detachFromTarget", { sessionId })
        .catch(() => {});
    },
  };
}

async function waitForAppServer() {
  for (let i = 0; i < 80; i += 1) {
    if (await isAppReachable()) return;
    await delay(250);
  }
  throw new Error(`PMS app is not reachable at ${BASE_URL}.`);
}

async function ensureAppServer() {
  if (await isAppReachable()) return null;

  if (APP_URL.port === "8000") {
    await waitForAppServer();
    return null;
  }

  const serverArgs = [
    "run",
    "dev",
    "--",
    "--host",
    APP_URL.hostname,
    "--port",
    APP_URL.port || "5175",
  ];

  const server =
    process.platform === "win32"
      ? spawn("cmd.exe", ["/d", "/s", "/c", `npm ${serverArgs.join(" ")}`], {
          env: { ...process.env, BROWSER: "none" },
          stdio: process.env.QA_VERBOSE_SERVER ? "inherit" : "ignore",
        })
      : spawn("npm", serverArgs, {
          env: { ...process.env, BROWSER: "none" },
          stdio: process.env.QA_VERBOSE_SERVER ? "inherit" : "ignore",
        });

  await waitForAppServer();
  return server;
}

async function evaluate(client, sessionId, expression, timeoutMs = COMMAND_TIMEOUT_MS) {
  return client.send(
    "Runtime.evaluate",
    {
      expression,
      returnByValue: true,
      awaitPromise: true,
    },
    sessionId,
    timeoutMs
  );
}

async function waitForCondition(client, sessionId, label, expression, timeoutMs = ROUTE_TIMEOUT_MS) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const result = await evaluate(client, sessionId, expression, 3000);
    if (result.result?.value) return;
    await delay(200);
  }
  throw new Error(`${label} was not ready after ${timeoutMs}ms`);
}

async function navigate(client, sessionId, url) {
  await client.send("Page.navigate", { url }, sessionId);
  await waitForCondition(
    client,
    sessionId,
    `DOM for ${url}`,
    `["interactive", "complete"].includes(document.readyState)`,
    10000
  );
}

function screenshotName(label, routeName, width, height) {
  return `${label}-${width}x${height}-${routeName}.png`;
}

function failedResult(routeName, path, label, width, height, error) {
  return {
    routeName,
    path,
    label,
    width,
    height,
    ok: false,
    error: error instanceof Error ? error.message : String(error),
  };
}

async function inspectRoute(client, routeName, path, expectedTitle, requiresAuth, label, width, height) {
  const { targetId } = await client.send("Target.createTarget", { url: "about:blank" });
  let pageClient;

  try {
    pageClient = await cdpTargetSession(client, targetId);

    await pageClient.send("Page.enable");
    await pageClient.send("Runtime.enable");
    await pageClient.send(
      "Emulation.setDeviceMetricsOverride",
      {
        width,
        height,
        deviceScaleFactor: label === "desktop" ? 1 : 2,
        mobile: label !== "desktop",
      }
    );

    await navigate(pageClient, undefined, `${BASE_URL}/login`);
    await evaluate(
      pageClient,
      undefined,
      requiresAuth
        ? `localStorage.setItem("guzo_pms_session", ${JSON.stringify(
            JSON.stringify(adminSession)
          )})`
        : `localStorage.removeItem("guzo_pms_session")`
    );

    await navigate(pageClient, undefined, `${BASE_URL}${path}`);

    if (requiresAuth) {
      await waitForCondition(
        pageClient,
        undefined,
        `${path} app shell`,
        `Boolean(document.querySelector('[data-testid="pms-app-shell"]'))`
      );
    } else {
      await waitForCondition(
        pageClient,
        undefined,
        `${path} login page`,
        `location.pathname === "/login" && document.body.innerText.length > 0`
      );
    }

    await delay(300);

    const inspection = await evaluate(
      pageClient,
      undefined,
      `(() => {
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const all = Array.from(document.querySelectorAll("*"));
        const interactive = Array.from(document.querySelectorAll("button, a, input, select, textarea"));
        const isVisible = (el) => Boolean(el && el.getBoundingClientRect().width && el.getBoundingClientRect().height);
        const titles = Array.from(document.querySelectorAll(".page-title-row h1, .page-heading"))
          .filter(isVisible)
          .map((el) => (el.textContent || "").trim());
        const shellVisible = Boolean(document.querySelector('[data-testid="pms-app-shell"]'));
        const horizontalOverflow = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - viewportWidth;
        const outOfViewport = interactive
          .map((el) => {
            const rect = el.getBoundingClientRect();
            return {
              tag: el.tagName,
              text: (el.textContent || el.value || "").trim().slice(0, 80),
              left: Math.round(rect.left),
              right: Math.round(rect.right),
              width: Math.round(rect.width),
            };
          })
          .filter((item) => item.width > 0 && (item.left < -1 || item.right > viewportWidth + 1));
        const clippedControls = interactive
          .filter((el) => el.clientWidth > 0 && (el.scrollWidth > el.clientWidth + 2 || el.scrollHeight > el.clientHeight + 4))
          .map((el) => ({ tag: el.tagName, text: (el.textContent || el.value || "").trim().slice(0, 80) }));
        const tooWideElements = all
          .map((el) => {
            const rect = el.getBoundingClientRect();
            return {
              tag: el.tagName,
              className: String(el.className || "").slice(0, 120),
              left: Math.round(rect.left),
              right: Math.round(rect.right),
              width: Math.round(rect.width),
            };
          })
          .filter((item) => item.width > viewportWidth + 2 || item.left < -2 || item.right > viewportWidth + 2)
          .slice(0, 8);
        return {
          title: document.title,
          path: location.pathname,
          viewportWidth,
          viewportHeight,
          shellVisible,
          expectedTitle: ${JSON.stringify(expectedTitle)},
          titles,
          titleVisible: ${JSON.stringify(expectedTitle === "Login")}
            ? location.pathname === "/login"
            : titles.includes(${JSON.stringify(expectedTitle)}),
          horizontalOverflow,
          outOfViewport,
          clippedControls,
          tooWideElements,
        };
      })();`
    );

    const screenshot = await pageClient.send(
      "Page.captureScreenshot",
      { format: "png", captureBeyondViewport: false },
      undefined,
      10000
    );
    const file = screenshotName(label, routeName, width, height);
    writeFileSync(join(OUT_DIR, file), Buffer.from(screenshot.data, "base64"));

    const data = inspection.result.value;
    const issues = [];
    if (requiresAuth && !data.shellVisible) issues.push("PMS shell was not visible.");
    if (!data.titleVisible) issues.push(`Expected title "${expectedTitle}" was not visible.`);
    if (data.horizontalOverflow > 2) issues.push(`Horizontal overflow: ${data.horizontalOverflow}px.`);
    if (data.outOfViewport.length) issues.push(`${data.outOfViewport.length} controls are outside the viewport.`);
    if (data.clippedControls.length) issues.push(`${data.clippedControls.length} controls are clipped.`);

    return {
      routeName,
      path,
      label,
      width,
      height,
      ok: issues.length === 0,
      issues,
      screenshot: file,
      ...data,
    };
  } finally {
    if (pageClient) await pageClient.close();
    await client.send("Target.closeTarget", { targetId }).catch(() => {});
  }
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  rmSync(OUT_DIR, { recursive: true, force: true });
  mkdirSync(OUT_DIR, { recursive: true });

  const results = [];
  let appServer = null;
  let browser = null;
  let client = null;

  try {
    console.log(`Responsive QA base URL: ${BASE_URL}`);
    console.log(`Responsive QA debug port: ${DEBUG_PORT}`);
    appServer = await ensureAppServer();

    const userDataDir = join(tmpdir(), "guzo-edge-responsive-qa");
    rmSync(userDataDir, { recursive: true, force: true });
    mkdirSync(userDataDir, { recursive: true });

    browser = spawn(
      EDGE_PATH,
      [
        "--headless=new",
        `--remote-debugging-port=${DEBUG_PORT}`,
        `--user-data-dir=${userDataDir}`,
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
      ],
      { stdio: "ignore" }
    );

    const version = await waitForDebugger();
    client = await cdpSocket(version.webSocketDebuggerUrl);

    for (const [label, width, height] of viewports) {
      for (const [routeName, path, expectedTitle, requiresAuth] of routes) {
        const startedAt = Date.now();
        console.log(`[start] ${label} ${width}x${height} ${path}`);
        try {
          const result = await withTimeout(
            inspectRoute(client, routeName, path, expectedTitle, requiresAuth, label, width, height),
            ROUTE_TIMEOUT_MS,
            `${label} ${path}`
          );
          results.push({ ...result, durationMs: Date.now() - startedAt });
          console.log(
            `[${result.ok ? "ok" : "fail"}] ${label} ${path} ${Date.now() - startedAt}ms`
          );
        } catch (error) {
          const result = failedResult(routeName, path, label, width, height, error);
          results.push({ ...result, durationMs: Date.now() - startedAt });
          console.log(`[error] ${label} ${path}: ${result.error}`);
        } finally {
          writeFileSync(REPORT_FILE, JSON.stringify(results, null, 2));
        }
      }
    }
  } finally {
    writeFileSync(REPORT_FILE, JSON.stringify(results, null, 2));
    if (client) client.close();
    if (browser) browser.kill();
    if (appServer) appServer.kill();
  }

  const failed = results.filter((result) => !result.ok);
  console.log(`Report: ${REPORT_FILE}`);
  console.log(`Screenshots: ${OUT_DIR}`);
  console.log(`Responsive QA completed: ${results.length - failed.length}/${results.length} passed`);

  failed.forEach((result) => {
    console.log(`  ${result.label} ${result.path}: ${result.error || result.issues?.join(" ")}`);
  });

  if (failed.length) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  mkdirSync(OUT_DIR, { recursive: true });
  writeFileSync(
    REPORT_FILE,
    JSON.stringify(
      [
        {
          ok: false,
          error: error instanceof Error ? error.message : String(error),
        },
      ],
      null,
      2
    )
  );
  console.error(error);
  process.exit(1);
});
