# Installation

## Voraussetzungen

- Python 3.10 oder neuer
- ADB-Verbindung zum Gerät oder Emulator
- optional OpenCV für PNG-Template-Matching

## Linux

```bash
git clone https://github.com/Puzzle-Wulf/pns-wulf.git
cd pns-wulf
chmod +x pns-bot
python3 -m pip install -e ".[vision]"
./pns-bot setup
```

`adb_path` kann auf ein System-ADB gesetzt werden:

```text
adb
```

## Windows

```powershell
git clone https://github.com/Puzzle-Wulf/pns-wulf.git
cd pns-wulf
py -3 -m pip install -e ".[vision]"
.\pns-bot.cmd setup
```

Das Repository enthält einen Windows-ADB-Fallback unter `vendor/platform-tools/windows/adb.exe`.
