# steam-workshop-downloader

*Проект задумывался для закрепления асинхронного программирования на Python.*

## Что это такое

Данная программа позволяет скачивать указанные пользователем моды из Steam
Workshop и затем автоматически распаковывать архивы в указанную им же папку.

Для добавления списка модов для определённой игры создайте копию файла
`config/example.yml` в папке `config/`, укажите путь к игре и список модов.

## Пример использования для Civilization VI

В папке `config/` файл `civilization6.yml` имеет следующее содержание:

```yml
download_path: c:\Users\pepe\Documents\My Games\Sid Meier's Civilization VI\Mods
mods:
  - 1601259406 # Enhanced Mod Manager

  # UI
  - 2471091953 # Diplomacy Compatibility Patch

  - 1360462633 # Extended Diplomacy Ribbon
  - 873246701 # Better Trade Screen
  - 872296228 # Better Espionage Screen
  - 1312585482 # Better Report Screen (UI)
  - 2114277246 # Better Climate Screen (UI)
  - 2139486665 # Better World Rankings (UI)
  - 2495851756 # Better City States (UI)
  - 2460661464 # Quick Deals
  - 939149009 # Sukritact's Simple UI Adjustments
  - 2115302648 # CQUI - Community Quick User Interface

  - 2266952591 # Extended Policy Cards
  - 2428969051 # Detailed Map Tacks

  - 1679150838 # Colorized Historic Moments
  - 882664162 # Unique District Icons

  # Gameplay
  - 911395113 # Good Goody Huts
  - 1958135962 # Better Balanced Starts (BBS)
  - 1947948094 # HotFixes
  # (Real Tech Tree) Есть опциональная настройка: Governments
  # https://steamcommunity.com/sharedfiles/filedetails/?id=871465857
  - 871465857 # Real Tech Tree
  - 875009475 # Real Science Pace
  # (Real Era Stop) Do NOT use "No turn limit" option when setting up a game.
  # It will make the game progress to the era past the last one causing issues
  # with World Congress.
  # If you want to play longer, use custom turn limit
  # and set it to e.g. 1000 or bigger.
  - 880843004 # Real Era Stop

  # Multiplayer
  - 1431485535 # Fast Dynamic Timer

  # Other
  - 1916397407 # Better Spectator Mod (BSM)
  - 1658551717 # Quick Start
```

*__Примечание:__ как указано в файле `config/example.yml`, можно
указывать как id модов (`2266952591`), так и ссылки на них
(`https://steamcommunity.com/sharedfiles/filedetails/?id=2266952591`)*

Таким образом, все указанные моды будут скачаны, а затем помещены по пути
`c:\Users\pepe\Documents\My Games\Sid Meier's Civilization VI\Mods` в свои
отдельные папки.

## Требования для запуска

- `python 3.8+`
- `poetry`

## Запуск для использования программы, а не для разработки

```bash
poetry install --no-dev
poetry shell
python main.py
```

Программа пройдётся по всем файлам в папке `config/`, скачает указанные моды в
каждом и поместит их в указанные папки.

## Разработка

### Запуск

```bash
poetry install
poetry shell
python main.py
```

### Тестирование

```bash
pytest
```
