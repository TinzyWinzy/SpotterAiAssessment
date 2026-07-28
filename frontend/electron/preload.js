const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("truckledger", {
  platform: process.platform,
  versions: {
    node: process.versions.node,
    electron: process.versions.electron,
  },
});
