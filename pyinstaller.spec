from PyInstaller.utils.hooks import collect_submodules
import importlib.util


block_cipher = None

entry_script = "src/pdfnormal/main.py"

hiddenimports = [
    *collect_submodules("fitz"),
]

# User-requested hidden import. Only include if present to avoid failing
# the build when the module doesn't exist in the build environment.
if importlib.util.find_spec("logica") is not None:
    hiddenimports.append("logica")

a = Analysis(
    [entry_script],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
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
    name="PDF Normal",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

