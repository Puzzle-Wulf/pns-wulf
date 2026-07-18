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

## Koordinate kalibrieren

```bash
./pns-bot click-event set donate --x 512 --y 840
```

Die Koordinate wird in `config/click_events.json` gespeichert und hat Vorrang vor dem PNG-Matching.

## PNG bearbeiten

1. Screenshot erzeugen.
2. Zielbutton eng ausschneiden.
3. Datei als PNG speichern.
4. Registrieren:

```bash
./pns-bot click-event template donate --file ~/Desktop/donate.png
```
