# Desktop Packaging Guide

This folder contains the Electron wrapper that turns the React + FastAPI catalog project into a Windows desktop application.

## Folder Structure

```text
project/
  backend/
    desktop_server.py
    main.py
    runtime_paths.py
    images/
    aquant_catalog_full.xlsx
    catalog.pdf
    Kohler.pdf
  frontend/
    build/
    src/
  desktop/
    main.js
    preload.js
    loading.html
    package.json
    scripts/
      build-backend.ps1
```

## What Electron Does

- Starts the FastAPI backend automatically in the background on port `8000`
- Waits for the `/health` endpoint to respond
- Opens the React UI as the desktop window
- Bundles the React production build and PyInstaller backend into a Windows installer or portable `.exe`

## Development

From `project/desktop`:

```powershell
npm install
npm run dev
```

This starts:

- React dev server on `http://localhost:3000`
- Electron window
- FastAPI backend in the background

## Production Build

1. Build the React app
2. Build the backend executable with PyInstaller
3. Package everything with Electron Builder

From `project/desktop`:

```powershell
npm install
npm run make:exe
```

## Build Commands

```powershell
npm run build:frontend
npm run build:backend
npm run dist
```

Generated desktop artifacts are written to:

```text
project/desktop/release/
```
