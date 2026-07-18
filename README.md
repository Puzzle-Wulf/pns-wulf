# PNS-Wulf v1.33.7a

PNS-Wulf ist ein modularer ADB-Automationsbot für **Puzzle & Survival**. Jeder Prozess verwaltet genau eine ADB-Instanz. `start` initialisiert nur die Runtime; Task-Queues werden ausschließlich mit `play` gestartet.

Repository: `https://github.com/Puzzle-Wulf/pns-wulf`

## Neu in v1.33.7a

- vollständig modularisierte Python-Struktur unter `src/pns_wulf/`
- fehlende Klickbedingung pausiert die Ausführung statt blind weiterzuklicken
- Screenshot-Export direkt auf den Desktop oder nach `~/Pictures/Screenshots`
- dauerhafte Klickkoordinaten pro Event
- PNG-Template-Matching mit optionalem OpenCV
- private Geräte-/Accountdaten aus dem öffentlichen Repository entfernt
- vollständige GitHub-Dokumentation in `INDEX.md` und `wiki/`

## Schnellstart

### Linux

```bash
chmod +x ./pns-bot
./pns-bot setup
./pns-bot start
```

### Windows

```powershell
.\pns-bot.cmd setup
.\pns-bot.cmd start
```

Für Template-Matching:

```bash
python3 -m pip install -e ".[vision]"
```

## Queue ausführen

Dry-Run:

```bash
./pns-bot play --queue default_q1
```

Mit echten Klicks:

```bash
./pns-bot play --queue default_q1 --execute
```

## Fehlendes Click-Event

Wird beispielsweise `assets/click-events/help_all.png` nicht gefunden oder liegt der Match-Score unter dem Schwellwert, pausiert die Queue. Der Bot zeigt das betroffene Event, die erwartete PNG-Datei und die möglichen Reparaturbefehle an.

Screenshot auf den Desktop:

```bash
./pns-bot screenshot --destination Desktop
```

Screenshot nach `/home/$USER/Pictures/Screenshots`:

```bash
./pns-bot screenshot --destination Userhome
```

Koordinaten speichern:

```bash
./pns-bot click-event set help_all --x 512 --y 840
```

PNG registrieren:

```bash
./pns-bot click-event template help_all --file ~/Desktop/help_all.png --threshold 0.86
```

Im interaktiven Pause-Modus sind außerdem diese Eingaben möglich:

```text
retry
screenshot Desktop
screenshot Userhome
coords 512 840
skip
abort
```

## Wichtige Dokumentation

- [Projektindex](INDEX.md)
- [Installation](wiki/Installation.md)
- [Screenshot und Kalibrierung](wiki/Screenshot-and-Calibration.md)
- [Click-Event-System](wiki/Click-Event-System.md)
- [CLI-Referenz](wiki/CLI-Reference.md)
- [Migration von v2.4](wiki/Migration-v2.4-to-v1.33.7a.md)
