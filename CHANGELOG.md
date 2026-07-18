# Changelog

## v1.33.7a — 2026-07-18

### Added

- `screenshot --destination Desktop`
- `screenshot --destination Userhome`
- `click-event set`, `template`, `show`, `list`, `remove`
- Pause-State unter `runtime/pause-state.json`
- interaktiver und nicht-interaktiver Wiederaufnahme-Modus
- optionales OpenCV-Template-Matching
- GitHub-Wiki und CI-Konfiguration

### Changed

- vollständige Modularisierung unter `src/pns_wulf/`
- globale Projektversion auf `v1.33.7a`
- ADB-Binaries nach `vendor/platform-tools/windows/` verschoben
- private Konfiguration und Charakterdaten aus dem Repository entfernt

### Compatibility

- `pns_bot.py`, `pns-bot.sh`, `pns-bot.cmd` und die bisherigen `.cmd`-Kurzstarter bleiben erhalten.
