# Migration from v2.4 to v1.33.7a

## Übernehmen

- eigene `characters`-Liste
- `serial`, `package_name`, Host- und IRC-Einstellungen
- eigene Queue-Anpassungen
- selbst erstellte PNG-Sprites

## Nicht direkt kopieren

Die alte `config/pns_bot_config.json` kann private Daten enthalten. Übertrage nur benötigte Werte in eine neue, per `setup` erzeugte Datei.

## Pfadänderungen

| Alt | Neu |
|---|---|
| `platform-tools/` | `vendor/platform-tools/windows/` |
| monolithisches `pns_bot.py` | `src/pns_wulf/` plus Kompatibilitätsstarter |
| implizite/fehlende Click-Auflösung | `config/click_events.json` und Pause-Modus |

Alle strukturierten Runtime-Daten verwenden nun die Version `v1.33.7a`.
