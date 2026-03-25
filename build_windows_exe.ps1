param(
  [string]$PythonLauncher = "py",
  [string]$PythonVersion = "3.11.9",
  [string]$Config = "Release"
)

Write-Host "Building Windows .exe with PyInstaller..."

# Ensure we fail fast on errors.
$ErrorActionPreference = "Stop"

# Create venv (optional but recommended for reproducibility).
if (-not (Test-Path ".venv")) {
  Write-Host "Creating venv with Python $PythonVersion..."
  & $PythonLauncher -$PythonVersion -m venv .venv
}

$venvPython = ".venv\Scripts\python.exe"
$venvPip = ".venv\Scripts\pip.exe"

Write-Host "Installing dependencies..."
& $venvPip install --upgrade pip
& $venvPip install -r requirements.txt
& $venvPip install pyinstaller

Write-Host "Running PyInstaller..."
# Output will be placed in ./dist/
& $venvPython -m PyInstaller --noconfirm --clean pyinstaller.spec

Write-Host "Done. Check ./dist/ for the executable."

