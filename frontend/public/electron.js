const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const isDev = !app.isPackaged;
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, '../src/preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  });

  win.loadURL('http://localhost:3000');
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith('http://localhost:3000')) {
      event.preventDefault();
    }
  });
  if (isDev) {
    win.webContents.openDevTools();
  }
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
