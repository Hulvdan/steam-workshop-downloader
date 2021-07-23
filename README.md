# steam-workshop-downloader

*Проект задумывался для закрепления асинхронного программирования на Python.*

![steam-workshop-downloader](https://i.imgur.com/3Sfx0py.png)

## Что это такое

Данная программа позволяет скачивать указанные пользователем моды из Steam.
Workshop и затем автоматически распаковывать архивы в указанную им же папку.

Для добавления списка модов для определённой игры создайте копию файла
`config/example.yml` в папке `config/`, укажите путь к игре и список модов.

## Пример конфига для Civilization VI

В папке `config/` файл `civilization6.yml` имеет следующее содержание:

```yml
# Это сборник классных модов, которые мне понравились.
#
# Кроме косметических модов, здесь присутствуют те, которые радикально меняют
# геймплей, например, Real Tech Tree и Real Science Pace.
#
# Для того, чтобы настроить Real Tech Tree для использования всех возможностей,
# измените содержание файла 871465857_real_tech_tree/RTT_Govs.sql:
# Замените значение параметра RTT_OPTION_GOVS на '1':
# INSERT INTO GlobalParameters (Name, Value) VALUES ('RTT_OPTION_GOVS', '1');
#
# Также, если у вас включен мод Real Era Stop, не используйте "No turn limit"
# опцию при создании игры, а просто установите побольше ходов.

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
  - 1691629919 # Better Leader Icon (UI)

  - 2266952591 # Extended Policy Cards
  - 2428969051 # Detailed Map Tacks

  - 1679150838 # Colorized Historic Moments
  - 882664162 # Unique District Icons

  # Gameplay
  - 911395113 # Good Goody Huts
  - 1958135962 # Better Balanced Starts (BBS)
  - 1947948094 # HotFixes
  # (Real Tech Tree) Есть опциональная настройка: Governments.
  # Конфигурация описана в начале файла.
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
(`https://steamcommunity.com/sharedfiles/filedetails/?id=2266952591`).*

Таким образом, будут скачаны архивы всех
перечисленных модов, а затем распакованы по пути
`c:\Users\pepe\Documents\My Games\Sid Meier's Civilization VI\Mods`
в отдельные папки.

## Скачать и запустить

Перейдите в раздел **Releases**, скачайте архив `steam-workshop-downloader.zip`,
распакуйте и запустите файл `main.exe`.

## Разработка

### Требования для запуска

- `python 3.9.*`
- `poetry`

### Запуск

Необходимо активировать виртуальное окружение перед запуском основного скрипта.

```bash
poetry install # установка виртуального окружения
poetry shell # активация в.о.
python main.py
```

### Тестирование

Использовать `pytest` для тестирования.
