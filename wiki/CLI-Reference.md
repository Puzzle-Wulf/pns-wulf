# CLI Reference

## Runtime

```bash
./pns-bot setup
./pns-bot start
./pns-bot play --queue default_q1
./pns-bot play --queue default_q1 --execute
./pns-bot play --one-character
```

## Screenshots

```bash
./pns-bot screenshot --destination Desktop
./pns-bot screenshot --destination Userhome
```

## Click-Events

```bash
./pns-bot click-event list
./pns-bot click-event show help_all
./pns-bot click-event set help_all --x 512 --y 840
./pns-bot click-event template help_all --file ~/Desktop/help_all.png --threshold 0.86
./pns-bot click-event remove help_all
```

## Tasks und Queues

```bash
./pns-bot tasks
./pns-bot task-show alliance_research
./pns-bot task-edit alliance_research --cooldown 3600
./pns-bot task-import recordings/custom.task.json
./pns-bot task-recorder
./pns-bot queue list
./pns-bot queue show default_q1
./pns-bot queue new farm_daily --description "Farm Daily"
./pns-bot queue add alliance_research --queue farm_daily
./pns-bot queue use farm_daily
```
