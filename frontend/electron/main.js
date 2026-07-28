const { app, BrowserWindow, shell } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let mainWindow = null;
let backendProcess = null;

const isDev = process.env.NODE_ENV === "development";
const BACKEND_PORT = process.env.BACKEND_PORT || "8001";

function startBackend() {
  const backendDir = path.join(__dirname, "..", "..", "backend");

  backendProcess = spawn("python", ["manage.py", "runserver", `0.0.0.0:${BACKEND_PORT}`, "--noreload"], {
    cwd: backendDir,
    stdio: "pipe",
    env: { ...process.env, DJANGO_SETTINGS_MODULE: "spotter_backend.settings" },
  });

  backendProcess.stdout.on("data", (data) => {
    console.log(`[Django] ${data}`);
  });

  backendProcess.stderr.on("data", (data) => {
    console.log(`[Django] ${data}`);
  });

  backendProcess.on("error", (err) => {
    console.error("Failed to start Django backend:", err);
  });

  return new Promise((resolve) => {
    setTimeout(resolve, 2000);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 600,
    title: "TruckLedger",
    icon: path.join(__dirname, "..", "public", "favicon.svg"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
    },
    autoHideMenuBar: true,
  });

  if (isDev) {
    mainWindow.loadURL(`http://localhost:5173`);
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  if (!isDev) {
    await startBackend();
  }
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (backendProcess) {
    backendProcess.kill();
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});
