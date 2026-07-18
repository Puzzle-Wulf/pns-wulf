# Configuration

Lokale Konfigurationen werden beim Setup aus den Beispieldateien erzeugt und nicht committed.

| Datei | Zweck |
|---|---|
| `config/pns_bot_config.json` | Gerät, ADB, Runtime und Pause-Verhalten |
| `config/task_queues.json` | aktive Queue und Task-Reihenfolge |
| `config/click_events.json` | PNG-Pfade, Schwellwerte und Koordinaten |

## Click-Event-Einstellungen

```json
{
  "pause_on_missing_click_event": true,
  "pause_poll_seconds": 3,
  "pause_timeout_seconds": 0,
  "click_match_threshold": 0.86,
  "validate_click_events_in_dry_run": false
}
```

`pause_timeout_seconds: 0` bedeutet unbegrenztes Warten.
