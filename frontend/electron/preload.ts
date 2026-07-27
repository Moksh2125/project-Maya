// Electron preload — exposes a safe IPC bridge to the renderer via contextBridge
import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("maya", {
  // Window controls
  minimizeWindow: () => ipcRenderer.send("window:minimize"),
  maximizeWindow: () => ipcRenderer.send("window:maximize"),
  closeWindow:    () => ipcRenderer.send("window:close"),

  // Backend WebSocket helper (returns the WS URL)
  wsUrl: () => "ws://localhost:8000/ws",
});

// Type augmentation for renderer-side usage
export type MayaAPI = typeof window.maya;
