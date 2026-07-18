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
task-recorder> tap-event donate
task-recorder> save
```

Danach:

```bash
./pns-bot task-import recordings/alliance_research_custom.task.json
```

Für feste Koordinaten bleibt `tap 512 840 donate_button` verfügbar.
