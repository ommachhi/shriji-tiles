const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("desktopConfig", {
  backendUrl: process.env.ELECTRON_BACKEND_URL || "http://127.0.0.1:8000",
  isDesktop: true,
  platform: process.platform,
});
