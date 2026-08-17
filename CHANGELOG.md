# Changelog

## Unreleased

### Added

- geführter Task Builder für `tap`, `scroll` und numerischen `text_input`
- Screenshot-Crop-Workflow für Click-Event-Assets
- optionale Zwei-Finger-Bereichserfassung über ADB-Multitouch-Events
- Regressionstests für Click-Event-, Recording- und Sprite-Archivpfade
- Manifest-Prüfung für Version, Task-/Area-/Screen-Zähler und unterstützte Entry-Points

### Changed

- Vision-Abhängigkeiten zwischen `pyproject.toml` und `requirements-vision.txt` vereinheitlicht
- Installations- und Projektstruktur-Dokumentation an die neuen Capture-Module und Pillow-Abhängigkeit angepasst
- Beispiel-Accountdaten und den letzten hardcodierten Account-Fallback neutralisiert
- veraltetes Root-Verzeichnis `pns_character_db/` entfernt; Charakterdatenbanken liegen unter `runtime/characters/`
- CI auf minimale `contents: read`-Rechte, credential-freien Checkout, unabhängige Matrix-Jobs und ein Job-Timeout gehärtet
- Contributor- und Security-Regeln für bewusst freigegebene Git-LFS-Research-Artefakte präzisiert
- Screenshot-Dateinamen um eine Subsekunden-Komponente erweitert, damit schnelle Captures einander nicht überschreiben
- Cluster-HTTP-Antworten und fehlgeschlagene IRC-TLS-Sockets werden deterministisch geschlossen
- `MANIFEST.json` um den unterstützten Entry-Point `pns-bot.sh` ergänzt

### Fixed

- falscher Config-Pfad in der Fehlermeldung von `click-event capture`
- automatisch erzeugte Click-Event-Asset-Pfade gegen `..`, Slash- und absolute/Drive-Pfadbestandteile abgesichert
- Task-Recording-Dateinamen auf das Verzeichnis `recordings/` begrenzt
- Sprite-/APK-/XAPK-Extraktion verwirft unsichere Archivpfade vor dem Schreiben

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
