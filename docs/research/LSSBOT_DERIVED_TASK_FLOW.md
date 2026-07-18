# LSSBot-derived Task Flow

This file maps the JAR-discovered PAS API classes into the PNS-Bot query-loop model. The bot checks state first, then clicks only if the check says the step is needed.

## Core flow

1. ADB connects to one Android device.
2. Start Puzzle & Survival package.
3. Wait until a back/menu state is visible.
4. Open/read character window where configured.
5. Create or open `<CHARACTERNAME>.db`.
6. For every task: check cooldown, check screen, check availability, act, then update cooldown.

## JAR API mapping

- PASMenu: back/menu handling and OCR/OpenCV methods
- PASAlliance: openAlliance/isMenuOpen/open alliance tabs
- PASDispatch/PASMarch: dispatch/march actions
- PASDailyToDoMenu: daily menu / research lab
- PASAutoUseResource: resource item use/insufficient-resource UI
- PASBuildingUpgrading/PASBuildingLocator: base building detection and upgrade flow
