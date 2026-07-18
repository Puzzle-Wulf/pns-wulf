# Click-Event System

## Auflösungsreihenfolge

1. direkte `x`/`y`-Koordinate im Task-Step
2. gespeicherte Koordinate in `config/click_events.json`
3. PNG-Vorlage aus Task oder Registry
4. Standardpfad `assets/click-events/<target>.png`

## Pause-Verhalten

Kann ein notwendiges Event nicht aufgelöst werden, wird `runtime/pause-state.json` geschrieben. Die Queue klickt nicht weiter.

Interaktiv:

```text
paused> screenshot Desktop
paused> screenshot Userhome
paused> coords 512 840
paused> retry
paused> skip
paused> abort
```

Nicht-interaktiv prüft der Prozess die Registry und PNG-Datei im konfigurierten Polling-Intervall erneut. Ein parallel ausgeführtes `click-event set` setzt die Queue automatisch fort.

## Template-Matching

OpenCV nutzt `TM_CCOEFF_NORMED`. Der Standard-Schwellwert ist `0.86`. Pro Event kann ein eigener Wert gesetzt werden.
