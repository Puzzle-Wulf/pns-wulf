# Troubleshooting

## ADB nicht gefunden

Setze `adb_path` auf `adb` oder einen absoluten Pfad. Unter Windows ist `vendor/platform-tools/windows/adb.exe` enthalten.

## PNG fehlt

```bash
./pns-bot screenshot --destination Desktop
./pns-bot click-event template EVENT --file ~/Desktop/EVENT.png
```

## Koordinate statt PNG verwenden

```bash
./pns-bot click-event set EVENT --x 500 --y 900
```

## Queue bleibt pausiert

Prüfe `runtime/pause-state.json`, den Eventnamen, den Templatepfad und den Match-Score. Danach im interaktiven Terminal `retry` eingeben. Nicht-interaktive Prozesse prüfen automatisch erneut.

## OpenCV fehlt

```bash
python3 -m pip install -e ".[vision]"
```
