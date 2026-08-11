# Project Structure

```text
pns-wulf/
├── pns-bot / pns-bot.cmd
├── src/pns_wulf/
│   ├── __init__.py
│   ├── __main__.py
│   ├── adb.py
│   ├── automation.py
│   ├── cli.py
│   ├── click_events.py
│   ├── cluster.py
│   ├── configuration.py
│   ├── constants.py
│   ├── database.py
│   ├── irc.py
│   ├── paths.py
│   ├── runtime.py
│   ├── screenshots.py
│   ├── sprites.py
│   ├── task_store.py
│   ├── template_capture.py
│   ├── touch_capture.py
│   └── util.py
├── config/
├── data/
├── assets/click-events/
├── sprites/
├── runtime/
├── recordings/
├── tests/
└── wiki/
```

Die Root-Starter bleiben klein; die Programmlogik liegt vollständig im Python-Paket.

`template_capture.py` enthält den Screenshot-/Crop-Workflow für Click-Event-Assets. `touch_capture.py` liest Multitouch-Punkte über ADB und übersetzt sie für den geführten Tap-Workflow in Screenshot-Bereiche.
