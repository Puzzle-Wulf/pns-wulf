# Click-Event PNGs

Pro Event liegt eine möglichst eng zugeschnittene PNG-Datei unter:

```text
assets/click-events/<event-name>.png
```

Beispiel:

```text
assets/click-events/help_all.png
```

## Empfohlen: direkt aus einem Screenshot ausschneiden

Vorhandenen Screenshot öffnen, Zielbereich mit der Maus markieren und automatisch registrieren:

```bash
./pns-bot click-event crop help_all --file ~/Desktop/screen.png
```

Oder zuerst live per ADB aufnehmen:

```bash
./pns-bot click-event capture help_all
```

Ohne GUI kann der Bereich direkt angegeben werden:

```bash
./pns-bot click-event crop help_all --file ~/Desktop/screen.png --region 420,730,180,80
```

Format: `x,y,width,height`.

Im Task Recorder erledigt `image help_all` Aufnahme, Auswahl, Speicherung, Registrierung und das Hinzufügen des `tap_area`-Steps in einem Ablauf.

## Vorhandene zugeschnittene Datei registrieren

```bash
./pns-bot click-event template help_all --file ~/Desktop/help_all.png
```
