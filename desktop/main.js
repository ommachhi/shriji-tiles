const { app, BrowserWindow, dialog } = require("electron");
const fs = require("fs");
const http = require("http");
const path = require("path");
const { spawn } = require("child_process");

const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = 8000;
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;

let mainWindow = null;
let backendProcess = null;
let shuttingDown = false;

function log(message) {
  console.log(`[desktop] ${message}`);
}

function resolveFrontendEntry() {
  if (!app.isPackaged && process.env.ELECTRON_START_URL) {
    return { type: "url", value: process.env.ELECTRON_START_URL };
  }

  const filePath = app.isPackaged
    ? path.join(process.resourcesPath, "frontend-build", "index.html")
    : path.join(__dirname, "..", "frontend", "build", "index.html");

  return { type: "file", value: filePath };
}

function waitForHttpUrl(url, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;

  return new Promise((resolve, reject) => {
    const attempt = () => {
      const request = http.get(url, (response) => {
        if (response.statusCode && response.statusCode < 500) {
          response.resume();
          resolve();
          return;
        }

        response.resume();
        retry(new Error(`Request returned status ${response.statusCode}`));
      });

      request.setTimeout(2000, () => {
        request.destroy(new Error("Request timed out"));
      });

      request.on("error", retry);
    };

    const retry = (error) => {
      if (Date.now() >= deadline) {
        reject(error);
        return;
      }
      setTimeout(attempt, 500);
    };

    attempt();
  });
}

function resolveBackendLaunch() {
  if (app.isPackaged) {
    const executableName = process.platform === "win32" ? "ProductCatalogBackend.exe" : "ProductCatalogBackend";
    const cwd = path.join(process.resourcesPath, "backend");
    return {
      command: path.join(cwd, executableName),
      args: [],
      cwd,
    };
  }

  const backendDir = path.join(__dirname, "..", "backend");
  const windowsVenvPython = path.join(backendDir, "venv", "Scripts", "python.exe");
  const unixVenvPython = path.join(backendDir, "venv", "bin", "python");
  const command = fs.existsSync(windowsVenvPython)
    ? windowsVenvPython
    : fs.existsSync(unixVenvPython)
      ? unixVenvPython
      : "python";

  return {
    command,
    args: [path.join(backendDir, "desktop_server.py")],
    cwd: backendDir,
  };
}

function waitForBackendReady(timeoutMs = 30000) {
  return waitForHttpUrl(`${BACKEND_URL}/health`, timeoutMs);
}

function startBackend() {
  if (backendProcess && !backendProcess.killed) {
    return waitForBackendReady();
  }

  return new Promise((resolve, reject) => {
    const backend = resolveBackendLaunch();
    log(`Starting backend using ${backend.command}`);

    backendProcess = spawn(backend.command, backend.args, {
      cwd: backend.cwd,
      env: {
        ...process.env,
        BACKEND_HOST,
        BACKEND_PORT: String(BACKEND_PORT),
        PYTHONUNBUFFERED: "1",
      },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });

    backendProcess.stdout.on("data", (chunk) => {
      process.stdout.write(`[backend] ${chunk}`);
    });

    backendProcess.stderr.on("data", (chunk) => {
      process.stderr.write(`[backend] ${chunk}`);
    });

    backendProcess.once("error", (error) => {
      reject(error);
    });

    backendProcess.once("exit", (code) => {
      if (!shuttingDown && code !== 0) {
        log(`Backend exited unexpectedly with code ${code}`);
      }
    });

    waitForBackendReady().then(resolve).catch(reject);
  });
}

async function loadFrontend() {
  const entry = resolveFrontendEntry();
  if (entry.type === "url") {
    await waitForHttpUrl(entry.value, 45000);
    await mainWindow.loadURL(entry.value);
    return;
  }

  await mainWindow.loadFile(entry.value);
}

function stopBackend() {
  if (!backendProcess || backendProcess.killed) {
    return;
  }

  try {
    backendProcess.kill();
  } catch (error) {
    log(`Failed to stop backend cleanly: ${error.message}`);
  }
}

async function createMainWindow() {
  process.env.ELECTRON_BACKEND_URL = BACKEND_URL;

  mainWindow = new BrowserWindow({
    width: 1500,
    height: 960,
    minWidth: 1200,
    minHeight: 760,
    show: false,
    autoHideMenuBar: true,
    backgroundColor: "#f4f7fb",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  await mainWindow.loadFile(path.join(__dirname, "loading.html"));
  mainWindow.show();

  try {
    await startBackend();
    await loadFrontend();
  } catch (error) {
    dialog.showErrorBox(
      "Application Startup Failed",
      [
        "The desktop app could not start the FastAPI backend.",
        "",
        `Reason: ${error.message}`,
        "",
        `Expected backend URL: ${BACKEND_URL}`,
      ].join("\n")
    );
    app.quit();
    return;
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(createMainWindow);

app.on("before-quit", () => {
  shuttingDown = true;
  stopBackend();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createMainWindow();
  }
});
