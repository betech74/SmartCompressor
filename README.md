# Smart Compressor

Smart Compressor is a Windows desktop app to analyze and compress images, videos, PDFs, and text files with a modern GUI, drag & drop, and progress tracking.

## Features
- Drag & drop folder support
- Automatic analysis with estimated size and gains
- Image / video / PDF / text compression
- GPU (NVENC) support when available
- Multi-language UI (FR / EN)
- Light & dark themes
- Detailed application logs + crash reports

## Requirements (Development)
- Python 3.10+ (recommended)
- Windows (GUI target)

Install dependencies:
```powershell
pip install -r requirements.txt
```

Optional dev tools:
```powershell
pip install -r requirements-dev.txt
```

## Run (Development)
From the project root:
```powershell
python -m gui.app
```

## Build (Release)
This project uses PyInstaller with a spec file.

```powershell
pyinstaller SmartCompressor.spec
```

The EXE is generated in:
- `dist/SmartCompressor/SmartCompressor.exe` (folder mode)

## Logs and Settings
User data is stored in `%APPDATA%\\SmartCompressor`:
- Settings: `settings/settings.json`
- Logs: `log/app.log`
- Crash logs: `log/CRASH-DD_MM_AAAA-HH_MM_SS.log`

If the app crashes, a dialog will ask to send the crash log to:
```
contact@betechinfo.fr
```

## Release Checklist
- Update version in `config.py`
- Run `ruff check .`
- Build with PyInstaller
- Smoke test the EXE

## License
Copyright BeTechInfo © - [www.betechinfo.fr](https://www.betechinfo.fr)
