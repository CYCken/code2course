# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('code2course_config.example.json', '.'), ('code2course_style.example.json', '.'), ('code2course_prompt.example.txt', '.')]
binaries = [('/opt/homebrew/bin/ffmpeg', '.')]
hiddenimports = ['google.generativeai', 'questionary', 'python_pptx', 'moviepy', 'moviepy.editor', 'imageio', 'imageio_ffmpeg', 'numpy', 'decorator', 'requests', 'urllib3', 'certifi', 'charset_normalizer', 'idna', 'PIL', 'pillow', 'websockets', 'aiohttp', 'python_dotenv', 'pydub']
tmp_ret = collect_all('moviepy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('edge_tts')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('imageio')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('python_dotenv')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
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
    a.binaries,
    a.datas,
    [],
    name='code2course',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
