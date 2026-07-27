// Electron main process — spawns the Python backend and hosts the Vite app
import { app, BrowserWindow, ipcMain } from "electron";
import { spawn, ChildProcess } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isDev = process.env.NODE_ENV !== "production";

let mainWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;

function spawnBackend(): void {
  const backendDir = path.join(__dirname, "../../backend");
  const python = process.platform === "win32" ? "python" : "python3";

  backendProcess = spawn(python, ["-m", "uvicorn", "main:app", "--port", "8000"], {
    cwd: backendDir,
    stdio: "pipe",
    shell: true,
  });

  backendProcess.stdout?.on("data", (d) => console.log("[Backend]", d.toString()));
  backendProcess.stderr?.on("data", (d) => console.error("[Backend ERR]", d.toString()));
  backendProcess.on("close", (code) => console.log(`[Backend] exited with code ${code}`));
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    frame: false,
    transparent: true,
    vibrancy: "under-window",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.on("closed", () => { mainWindow = null; });
}

app.whenReady().then(() => {
  spawnBackend();
  createWindow();
  app.on("activate", () => { if (!mainWindow) createWindow(); });
});

app.on("window-all-closed", () => {
  backendProcess?.kill();
  if (process.platform !== "darwin") app.quit();
});

// Window control IPC
ipcMain.on("window:minimize", () => mainWindow?.minimize());
ipcMain.on("window:maximize", () => {
  mainWindow?.isMaximized() ? mainWindow.unmaximize() : mainWindow?.maximize();
});
ipcMain.on("window:close", () => mainWindow?.close());
