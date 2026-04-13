$ErrorActionPreference = "Stop"

$desktopDir = Split-Path -Parent $PSScriptRoot
$projectDir = Split-Path -Parent $desktopDir
$backendDir = Join-Path $projectDir "backend"

$windowsPython = Join-Path $backendDir "venv\Scripts\python.exe"
$windowsPyInstaller = Join-Path $backendDir "venv\Scripts\pyinstaller.exe"

if (-not (Test-Path $windowsPython)) {
    throw "Backend virtual environment not found at $windowsPython"
}

Push-Location $backendDir

try {
    & $windowsPython -m pip install -r requirements.txt pyinstaller

    if (Test-Path "build") {
        Remove-Item -Recurse -Force "build"
    }

    if (Test-Path "dist\ProductCatalogBackend") {
        Remove-Item -Recurse -Force "dist\ProductCatalogBackend"
    }

    & $windowsPyInstaller `
        --noconfirm `
        --clean `
        --onedir `
        --name ProductCatalogBackend `
        --collect-all openpyxl `
        --collect-all reportlab `
        --collect-all pymupdf `
        --collect-submodules fitz `
        --hidden-import uvicorn.logging `
        --hidden-import uvicorn.loops.auto `
        --hidden-import uvicorn.protocols.http.auto `
        --hidden-import uvicorn.protocols.websockets.auto `
        --hidden-import uvicorn.lifespan.on `
        --add-data "$backendDir\aquant_catalog_full.xlsx;." `
        --add-data "$backendDir\catalog.pdf;." `
        --add-data "$backendDir\Kohler.pdf;." `
        --add-data "$backendDir\catalog_cache.json;." `
        --add-data "$backendDir\kohler_cache.json;." `
        --add-data "$backendDir\products.json;." `
        --add-data "$backendDir\images;images" `
        "$backendDir\desktop_server.py"

    Write-Host "Backend desktop bundle created at $backendDir\dist\ProductCatalogBackend"
}
finally {
    Pop-Location
}
