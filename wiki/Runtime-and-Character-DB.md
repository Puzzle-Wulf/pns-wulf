# Runtime and Character DB

Jeder Prozess verwaltet genau eine ADB-Serial. Mehrere Charaktere können nacheinander über dieselbe Instanz bearbeitet werden.

- Runtime-Status: `runtime/state.json`
- Pause-Status: `runtime/pause-state.json`
- Charakterdatenbanken: `runtime/characters/<CHARAKTER>.db`

Eine Datenbank enthält Cooldowns, Task-Events und Finalisierungsmetadaten.
