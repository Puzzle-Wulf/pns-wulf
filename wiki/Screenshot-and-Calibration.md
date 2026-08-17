# Screenshot and Calibration

## Desktop

```bash
./pns-bot screenshot --destination Desktop
```

Unter Linux wird `XDG_DESKTOP_DIR` aus `~/.config/user-dirs.dirs` berücksichtigt. Fehlt die Definition, wird `~/Desktop` verwendet.

## Userhome

```bash
./pns-bot screenshot --destination Userhome
```

Unter Linux lautet das Ziel:

```text
/home/$USER/Pictures/Screenshots
```

## Bildbereich direkt als Click-Event anlegen

Aus einem bereits vorhandenen Screenshot:

```bash
./pns-bot click-event crop donate --file ~/Desktop/screen.png
```

Es öffnet sich eine einfache Rechteck-Auswahl. Zielbereich mit der Maus markieren, mit `Enter` übernehmen, mit `Esc` abbrechen. Der Ausschnitt landet automatisch unter:

```text
assets/click-events/donate.png
```

Gleichzeitig wird das Template in `config/click_events.json` registriert. Bei späteren Task-Läufen sucht PNS-Wulf dieses Bild per OpenCV-Template-Matching und klickt auf dessen Mittelpunkt.

Direkt einen aktuellen ADB-Screenshot aufnehmen und ausschneiden:

```bash
./pns-bot click-event capture donate
```

Ohne grafische Oberfläche kann die Region explizit angegeben werden:

```bash
./pns-bot click-event crop donate --file ~/Desktop/screen.png --region 420,730,180,80
./pns-bot click-event capture donate --region 420,730,180,80
```

Format: `x,y,width,height`.

Die Bildauswahl benötigt die Vision-Abhängigkeiten:

```bash
pip install -e ".[vision]"
```

Auf Linux muss für die interaktive Auswahl zusätzlich Tkinter verfügbar sein. Ohne Tk/Display funktioniert weiterhin `--region`.

## Koordinate kalibrieren

```bash
./pns-bot click-event set donate --x 512 --y 840
```

Die Koordinate wird in `config/click_events.json` gespeichert und hat Vorrang vor dem PNG-Matching.

## PNG manuell bearbeiten

1. Screenshot erzeugen.
2. Zielbutton eng ausschneiden.
3. Datei als PNG speichern.
4. Registrieren:

```bash
./pns-bot click-event template donate --file ~/Desktop/donate.png
```
