# Task Recorder

```bash
./pns-bot task-recorder
```

## Geführter Builder

Beim Start fragt der Recorder direkt, was der erste Schritt tun soll:

```text
Was soll der erste Schritt tun? [tap/scroll/text/advanced]:
```

Danach können beliebig viele Schritte hintereinander aufgenommen werden:

```text
next-step> tap
next-step> scroll
next-step> text
next-step> show
next-step> done
```

`advanced` wechselt jederzeit in den bisherigen Kommandomodus.

## Tap: Zwei Finger markieren

Der bevorzugte Tap-Workflow ist:

1. `tap` wählen,
2. einen eindeutigen Target-/Asset-Namen eingeben,
3. zwei Finger auf gegenüberliegende Ecken des gewünschten Bereichs legen,
4. beide Finger liegen lassen,
5. am PC Enter drücken,
6. `pns-wulf` liest die beiden aktiven Multitouch-Punkte über `adb shell getevent`,
7. während die Finger noch liegen wird ein Screenshot aufgenommen,
8. die Touch-Koordinaten werden auf Screenshot-Pixel skaliert,
9. der Bereich zwischen beiden Punkten wird als `assets/click-events/<target>.png` ausgeschnitten,
10. ein `{"type": "tap_area", "target": "<target>"}`-Step wird gespeichert.

Bei späteren Task-Läufen sucht das vorhandene Template-Matching dieses Asset im aktuellen Screenshot und klickt auf dessen Mittelpunkt.

### Zwei-Finger-Fallback

Nicht jedes Android-Gerät erlaubt dem ADB-Shell-User Live-Zugriff auf `/dev/input`. Wenn kein lesbarer Multitouch-Stream verfügbar ist, nimmt der Recorder automatisch einen Screenshot auf und öffnet die bestehende grafische Rechteck-Auswahl. Dort den Bereich mit der Maus ziehen und mit Enter bestätigen.

Die Zwei-Finger-Auswahl injiziert selbst **keine** Multitouch-Geste. Sie beobachtet nur zwei echte Finger über die vom Gerät gelieferten `ABS_MT_*`-Events.

## Scroll

Für Scroll-Schritte muss kein Bild aufgenommen werden:

```text
next-step> scroll
Scroll-Richtung [down/up/left/right] (down):
```

Gespeichert wird zum Beispiel:

```json
{"type": "scroll", "direction": "down", "distance": 0.6, "duration_ms": 450}
```

Die Koordinaten werden absichtlich nicht im Task gespeichert. Beim Ausführen liest `pns-wulf` die aktuelle Displaygröße über ADB und berechnet daraus einen `adb shell input swipe` für die jeweilige Auflösung.

`down` bedeutet dabei: Inhalt nach unten scrollen. Dafür bewegt sich der simulierte Finger nach oben. `up`, `left` und `right` sind entsprechend ebenfalls Inhaltsrichtungen.

Im erweiterten Kommandomodus:

```text
task-recorder> scroll down
task-recorder> scroll down 0.60 450
```

## Numerischer Text-Input

Für Zahlenfelder:

```text
next-step> text
Zahl eingeben: 12345
```

Gespeichert wird:

```json
{"type": "text_input", "value": "12345"}
```

Nur Ziffern werden akzeptiert. Beim Ausführen verwendet der Task-Runner `adb shell input text`.

## Bisheriger Bild-/Kommandomodus

Der vorhandene Screenshot-Crop bleibt erhalten:

```text
task-recorder> new alliance_research_custom
task-recorder> name Alliance Research Custom
task-recorder> area ALLIANCE
task-recorder> check where_am_i
task-recorder> image donate
task-recorder> save
```

`image <target>` führt den bisherigen Bild-Schritt aus:

1. aktueller ADB-Screenshot wird aufgenommen,
2. Screenshot öffnet sich zur Rechteck-Auswahl,
3. der markierte Bereich wird unter `assets/click-events/<target>.png` gespeichert,
4. das Click-Event wird registriert,
5. der Recorder fügt `{"type": "tap_area", "target": "<target>"}` in den Task ein.

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
