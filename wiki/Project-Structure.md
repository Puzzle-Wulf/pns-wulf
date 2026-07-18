# Project Structure

```text
pns-wulf/
├── pns-bot / pns-bot.cmd
├── src/pns_wulf/
│   ├── cli.py
│   ├── configuration.py
│   ├── adb.py
│   ├── screenshots.py
│   ├── click_events.py
│   ├── automation.py
│   ├── runtime.py
│   ├── task_store.py
│   ├── database.py
│   ├── cluster.py
│   ├── irc.py
│   └── sprites.py
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
