# turing-smart-screen-python-HIDdev2

`turing-smart-screen-python-HIDdev2` — это модифицированный форк `turing-smart-screen-python` с поддержкой 3.5" SmartMonitor, который в Linux определяется как USB HID (`0483:0065`), а не как обычный serial/TTY-дисплей.

Основан на оригинальном проекте:

- https://github.com/mathoudebine/turing-smart-screen-python

## Что умеет проект

- работать с монитором через `hidraw`
- загружать темы в монитор по HID/YMODEM?
- передавать live-метрики CPU, GPU, RAM, disk и network
- работать с vendor-темами `.dat`
- конвертировать vendor `UI -> DAT`
- управлять темами через `configure.py`
- редактировать SmartMonitor UI через отдельный редактор с canvas-preview `480x320`

## Основные файлы

- `main.py` — основной запуск проекта
- `configure.py` — GUI-конфигуратор, выбор тем, импорт и конвертация
- `smartmonitor-theme-editor.py` — редактор SmartMonitor UI
- `tools/smartmonitor-theme-manager.py` — CLI-менеджер тем

## Рекомендуемая стартовая тема

Для самого стабильного старта:

- `res/themes/rog03-vendor.dat`

## Быстрый старт

Рекомендуемый вариант:

```bash
chmod +x install.sh
./install.sh
source venv/bin/activate
python3 configure.py
```

Альтернативный запуск через готовые launcher-скрипты без ручного `source venv/bin/activate`:

```bash
chmod +x install.sh run-configure.sh run-monitor.sh
./install.sh
./run-configure.sh
```

Полезные launcher-скрипты:

- `./run-configure.sh` — запускает `configure.py` через `venv/bin/python`
- `./run-monitor.sh` — запускает `main.py` через `venv/bin/python`
- `Save + run` внутри конфигуратора тоже работает с `./run-configure.sh` и сразу переводит запуск в `main.py`

Ручная установка:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 configure.py
```

Дальше:

1. выбрать `SmartMonitor HID (experimental)`
2. выбрать тему
3. нажать `Save and run`

## Диагностика первого запуска

Если монитор не определяется или темы не загружаются, выполните:

```bash
python3 tools/smartmonitor-theme-manager.py doctor
```

Для Linux можно установить готовое `udev`-правило для доступа к `hidraw` без ручного `chmod`:

```bash
sudo cp tools/99-smartmonitor-hiddev.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

После этого отключите и снова подключите монитор.

## Что изменено относительно оригинала

В форк добавлено:

- HID backend для SmartMonitor
- runtime для live-метрик без framebuffer
- загрузка тем `img.dat`
- конвертация `vendor .ui -> .dat`
- интеграция SmartMonitor в GUI
- отдельный редактор SmartMonitor UI

## Лицензия

Оригинальный проект распространяется под `GNU GPL v3`.

Это означает, что проект можно изменять и публиковать как форк, но:

- лицензию GPL-3.0 нужно сохранить
- notices об авторских правах удалять нельзя
- модифицированная версия должна быть явно помечена как изменённая
- исходный код модификаций при распространении тоже должен оставаться доступным по GPL

См. [LICENSE](./LICENSE).

## История изменений

История релизов доступна в [CHANGELOG.md](./CHANGELOG.md).

## Руководство по Edit UI

Подробный мануал по работе с SmartMonitor `Edit UI` доступен в [EDIT_UI_MANUAL.md](./EDIT_UI_MANUAL.md).

## 💰 Поддержать проект

Если проект оказался полезным, вы можете поддержать разработку донатом:

TON Wallet:

`UQAnWldcIWfwKUmnJN5kMqW5VY6SuVwTtrnRpDEE_rilh8Qj`

Bitcoin (BTC):

`bc1qelwv8jm2j9pughk5rte0fap2gzvyhtgzwglutf`

Ethereum (ETH):

`0x6Ab5F41A4eF61E6F7517f4D89f759c94500e66e1`

Любое пожертвование помогает поддерживать проект и мотивирует развивать его дальше. Спасибо! ❤️
