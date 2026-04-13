# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\Net\\OneDrive\\Desktop\\Tejeshkp\\project\\backend\\aquant_catalog_full.xlsx', '.'), ('C:\\Users\\Net\\OneDrive\\Desktop\\Tejeshkp\\project\\backend\\catalog.pdf', '.'), ('C:\\Users\\Net\\OneDrive\\Desktop\\Tejeshkp\\project\\backend\\Kohler.pdf', '.'), ('C:\\Users\\Net\\OneDrive\\Desktop\\Tejeshkp\\project\\backend\\catalog_cache.json', '.'), ('C:\\Users\\Net\\OneDrive\\Desktop\\Tejeshkp\\project\\backend\\kohler_cache.json', '.'), ('C:\\Users\\Net\\OneDrive\\Desktop\\Tejeshkp\\project\\backend\\products.json', '.'), ('C:\\Users\\Net\\OneDrive\\Desktop\\Tejeshkp\\project\\backend\\images', 'images')]
binaries = []
hiddenimports = ['uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.on']
hiddenimports += collect_submodules('fitz')
tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('reportlab')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pymupdf')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\Net\\OneDrive\\Desktop\\Tejeshkp\\project\\backend\\desktop_server.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ProductCatalogBackend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ProductCatalogBackend',
)
