# Development

```bash
python3 -m pip install -e ".[vision,dev]"
python3 -m compileall -q src
python3 -m unittest discover -s tests -v
```

Neue Click-Event-Typen gehören in `click_events.py`; die Ausführungslogik liegt in `automation.py`. Neue CLI-Befehle werden ausschließlich in `cli.py` registriert.
