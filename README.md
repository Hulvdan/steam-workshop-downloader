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
  - 2266952591 # Extended Policy Cards
  - 873246701 # Better Trade Screen
  - 882664162 # Unique District Icons
  - 911395113 # Good Goody Huts
  - 939149009 # Sukritact's Simple UI Adjustments
  - 1312585482 # Better Report Screen (UI)
  - 1431485535 # Fast Dynamic Timer
  - 1601259406 # Enhanced Mod Manager
  - 1658551717 # Quick Start
  - 1679150838 # Colorized Historic Moments
  - 1916397407 # Better Spectator Mod (BSM)
  - 1947948094 # HotFixes
  - 1958135962 # Better Balanced Starts (BBS)
  - 2115302648 # CQUI - Community Quick User Interface
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
poetry run main.py
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
