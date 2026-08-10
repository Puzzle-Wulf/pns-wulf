# Task Recorder

```bash
./pns-bot task-recorder
```

Beispiel:

```text
task-recorder> new alliance_research_custom
task-recorder> name Alliance Research Custom
task-recorder> area ALLIANCE
task-recorder> check where_am_i
task-recorder> image donate
task-recorder> save
```

`image <target>` führt den kompletten Bild-Schritt aus:

1. aktueller ADB-Screenshot wird aufgenommen,
2. Screenshot öffnet sich zur Rechteck-Auswahl,
3. der markierte Bereich wird unter `assets/click-events/<target>.png` gespeichert,
4. das Click-Event wird registriert,
5. der Recorder fügt `{"type": "tap_area", "target": "<target>"}` in den Task ein.

Damit sucht der Task bei späteren Läufen das aufgenommene Bild per Template-Matching und klickt auf dessen Mittelpunkt.

Ein vorhandener Screenshot kann ebenfalls verwendet werden:

```text
task-recorder> image donate "C:\Users\Name\Desktop\screen.png"
```

Ohne grafische Oberfläche kann die Region direkt mitgegeben werden. `-` bedeutet: aktuellen ADB-Screenshot verwenden.

```text
task-recorder> image donate - 420,730,180,80
```

Für die Bildauswahl werden die Vision-Abhängigkeiten benötigt:

```bash
pip install -e ".[vision]"
```

Danach:

```bash
./pns-bot task-import recordings/alliance_research_custom.task.json
```

Bestehende Click-Events können weiterhin direkt verwendet werden:

```text
task-recorder> tap-event donate
```

Für feste Koordinaten bleibt `tap 512 840 donate_button` verfügbar.
