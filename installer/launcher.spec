# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for CortexDashboard.exe

Kullanim (Windows uzerinde Python 3.10+ kurulduktan sonra):
    pip install pyinstaller -r ../python_server/requirements.txt
    pyinstaller --clean installer/launcher.spec

Cikti:
    dist/CortexDashboard/CortexDashboard.exe   (one-folder)
    dist/CortexDashboard.exe                   (one-file, alttaki block)
"""
from pathlib import Path

ROOT = Path(SPECPATH).parent

block_cipher = None

datas = [
    (str(ROOT / 'python_server' / 'final_model.pkl'), 'python_server'),
    (str(ROOT / 'python_server' / 'suggestions.json'), 'python_server'),
    (str(ROOT / 'python_server' / 'flask_api.py'), 'python_server'),
    (str(ROOT / 'dashboard' / 'static'), 'dashboard/static'),
    (str(ROOT / 'src' / 'main' / 'resources' / 'config.properties'),
     'src/main/resources'),
]

hidden = [
    'flask',
    'flask_cors',
    'joblib',
    'sklearn',
    'sklearn.feature_extraction.text',
    'sklearn.pipeline',
    'sklearn.linear_model',
    'waitress',
]

a = Analysis(
    [str(ROOT / 'scripts' / 'launcher.py')],
    pathex=[str(ROOT), str(ROOT / 'python_server')],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib'],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CortexDashboard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon=str(ROOT / 'installer' / 'cortex.ico') if (ROOT / 'installer' / 'cortex.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='CortexDashboard',
)
