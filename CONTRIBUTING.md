# Contributing

1. Fork oder Branch erstellen.
2. Virtuelle Umgebung anlegen.
3. `python -m pip install -e ".[vision,dev]"` ausführen.
4. Änderungen mit `python -m compileall src` und `python -m unittest discover -s tests -v` prüfen.
5. Keine privaten `config/*.json`, Datenbanken, Screenshots oder APK/XAPK-Dateien committen.
