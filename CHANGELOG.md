# Changelog

## Unreleased

### Added

- geführter Task Builder für `tap`, `scroll` und numerischen `text_input`
- Screenshot-Crop-Workflow für Click-Event-Assets
- optionale Zwei-Finger-Bereichserfassung über ADB-Multitouch-Events

### Changed

- Vision-Abhängigkeiten zwischen `pyproject.toml` und `requirements-vision.txt` vereinheitlicht
- Projektstruktur-Dokumentation an die neuen Capture-Module angepasst
- Beispiel-Accountdaten neutralisiert
- veraltetes Root-Verzeichnis `pns_character_db/` entfernt; Charakterdatenbanken liegen unter `runtime/characters/`

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
