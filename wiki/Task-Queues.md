# Task Queues

`start` führt keine Queue aus. Erst `play` startet die aktive oder angegebene Queue.

```bash
./pns-bot queue list
./pns-bot queue new farm_daily --description "Farm Daily ohne Kampf"
./pns-bot queue add speedup_help --queue farm_daily
./pns-bot queue use farm_daily
./pns-bot play --queue farm_daily --execute
```

Cooldowns werden pro Charakter in einer eigenen SQLite-Datenbank gespeichert.
