# Edit UI Manual / Руководство по Edit UI

This document explains how the SmartMonitor `Edit UI` workflow works in the project.
Этот документ объясняет, как устроен workflow `Edit UI` для SmartMonitor в проекте.

## 1. What `Edit UI` Opens / Что открывает `Edit UI`

**English**

`Edit UI` opens the source `.ui` file of the selected SmartMonitor theme in `smartmonitor-theme-editor.py`.

If the selected theme has a linked `source_ui` in `metadata.yaml`, that linked UI is opened.
If no linked UI is available, the program lets you choose a `.ui` file manually.

**Русский**

`Edit UI` открывает исходный `.ui` файл выбранной SmartMonitor-темы в `smartmonitor-theme-editor.py`.

Если у выбранной темы есть связанный `source_ui` в `metadata.yaml`, открывается именно этот UI.
Если связанного UI нет, программа предлагает выбрать `.ui` файл вручную.

## 2. Main Workflow / Основной порядок работы

**English**

Recommended workflow:

1. Open a theme through `Edit UI`
2. Select or create widgets
3. Change properties in the right-side fields
4. Click `Apply`
5. Click `Save UI`
6. Click `Compile DAT` or `Compile+Upload`

If you want to create a new variation instead of overwriting the current UI:

1. Open the theme
2. Edit it
3. Click `Save As`
4. Save into a new `.ui`
5. Compile that new UI into `.dat`

**Русский**

Рекомендуемый порядок работы:

1. Открыть тему через `Edit UI`
2. Выбрать или создать виджеты
3. Изменить свойства в полях справа
4. Нажать `Apply`
5. Нажать `Save UI`
6. Нажать `Compile DAT` или `Compile+Upload`

Если вы хотите сделать новую вариацию темы, а не перезаписывать текущий UI:

1. Открыть тему
2. Отредактировать её
3. Нажать `Save As`
4. Сохранить в новый `.ui`
5. Собрать этот новый UI в `.dat`

## 3. Save Buttons / Кнопки сохранения

### `Apply`

**English**

Applies the values from the form fields to the currently selected widget in memory.
It does **not** save the `.ui` file to disk yet.

**Русский**

Применяет значения из полей формы к текущему выбранному виджету в памяти.
Файл `.ui` на диск при этом **ещё не сохраняется**.

### `Save UI`

**English**

Saves the current `.ui` file back to the same source path.
This is the main save action when you are editing the current theme.

**Русский**

Сохраняет текущий `.ui` файл обратно по тому же пути.
Это основной способ сохранить изменения в текущей теме.

### `Save As`

**English**

Saves the current UI into a new `.ui` file.
Use this when you want to create a new custom variation without overwriting the original source.

**Русский**

Сохраняет текущий UI в новый `.ui` файл.
Используйте это, если хотите сделать новую пользовательскую вариацию темы и не перезаписывать исходник.

## 4. Compile Buttons / Кнопки сборки

### `Compile DAT`

**English**

Compiles the currently loaded `.ui` into a SmartMonitor `.dat` theme file.

Use this when:

- you want to rebuild the theme
- you want to import or test the resulting `.dat`
- you do not want to upload immediately

**Русский**

Собирает текущий `.ui` в SmartMonitor `.dat` тему.

Используйте это, если:

- хотите пересобрать тему
- хотите импортировать или проверить полученный `.dat`
- не хотите сразу заливать тему в монитор

### `Compile+Upload`

**English**

Compiles the current `.ui` into `.dat` and immediately uploads it to the monitor.

Use this for rapid iteration when editing a theme and checking the result on real hardware.

**Русский**

Собирает текущий `.ui` в `.dat` и сразу загружает тему в монитор.

Используйте это для быстрого цикла правка -> сборка -> проверка на реальном устройстве.

## 5. Widget Creation Buttons / Кнопки создания виджетов

### `Add Number`

**English**

Adds a numeric sensor widget.
Usually used for CPU, GPU, RAM, disk, network and similar live metrics.

**Русский**

Добавляет числовой виджет датчика.
Обычно используется для CPU, GPU, RAM, disk, network и других live-метрик.

### `Add DateTime`

**English**

Adds a date/time widget.
Use the `Date/time fmt` field to define the display format.

**Русский**

Добавляет виджет даты/времени.
Формат отображения задаётся через поле `Date/time fmt`.

### `Add Image`

**English**

Adds an image widget.
You can then choose the image file with `Browse Img`.

**Русский**

Добавляет image-виджет.
После этого картинку можно выбрать через `Browse Img`.

### `Add Progress`

**English**

Adds a progress bar widget.
Usually used for CPU/GPU/RAM/disk percentage-style values.

**Русский**

Добавляет виджет progress bar.
Обычно используется для значений типа CPU/GPU/RAM/disk в процентах.

## 6. Editing Buttons / Кнопки редактирования

### `Duplicate`

**English**

Duplicates the selected widget or widget group.

**Русский**

Дублирует выбранный виджет или группу виджетов.

### `Delete`

**English**

Deletes the selected widget or group.

**Русский**

Удаляет выбранный виджет или группу.

### `Undo`

**English**

Reverts the last editor action.

**Русский**

Отменяет последнее действие в редакторе.

### `Redo`

**English**

Restores the last undone action.

**Русский**

Возвращает отменённое действие.

## 7. Alignment and Layout Buttons / Кнопки выравнивания и расположения

### `Align Left`

**English**

Aligns selected widgets to the left edge of the reference selection.

**Русский**

Выравнивает выбранные виджеты по левому краю относительно опорного элемента.

### `Align Top`

**English**

Aligns selected widgets to the top edge.

**Русский**

Выравнивает выбранные виджеты по верхнему краю.

### `Align HCenter`

**English**

Aligns selected widgets by horizontal center.

**Русский**

Выравнивает выбранные виджеты по горизонтальному центру.

### `Align VCenter`

**English**

Aligns selected widgets by vertical center.

**Русский**

Выравнивает выбранные виджеты по вертикальному центру.

### `Center X`

**English**

Centers selected widgets on the canvas horizontally.

**Русский**

Центрирует выбранные виджеты по горизонтали холста.

### `Center Y`

**English**

Centers selected widgets on the canvas vertically.

**Русский**

Центрирует выбранные виджеты по вертикали холста.

### `Center Both`

**English**

Centers selected widgets on both axes.

**Русский**

Центрирует выбранные виджеты сразу по обеим осям.

### `Bring Front`

**English**

Moves selected widgets to the front of the draw order.

**Русский**

Перемещает выбранные виджеты на передний план по порядку отрисовки.

### `Send Back`

**English**

Moves selected widgets to the back of the draw order.

**Русский**

Перемещает выбранные виджеты на задний план по порядку отрисовки.

### `Select All`

**English**

Selects all widgets in the current UI.

**Русский**

Выбирает все виджеты в текущем UI.

### `Dist. H`

**English**

Distributes selected widgets horizontally.

**Русский**

Распределяет выбранные виджеты по горизонтали.

### `Dist. V`

**English**

Distributes selected widgets vertically.

**Русский**

Распределяет выбранные виджеты по вертикали.

## 8. Canvas Interaction / Работа с canvas

**English**

- Drag a widget to move it
- Drag resize handles to resize it
- Hold `Shift` while dragging/resizing to temporarily bypass snap-to-grid
- Use arrow keys for small position adjustments
- Use `Ctrl+A` to select all
- Use `Ctrl+Z` and `Ctrl+Y` for undo/redo

**Русский**

- Перетаскивайте виджет мышкой для перемещения
- Тяните за resize handles для изменения размера
- Удерживайте `Shift` во время drag/resize, чтобы временно отключить snap-to-grid
- Используйте стрелки для точной подстройки позиции
- Используйте `Ctrl+A` для выбора всех
- Используйте `Ctrl+Z` и `Ctrl+Y` для undo/redo

## 9. Sensor Mapping / Привязка датчиков

**English**

For new themes, live sensor values are pulled into widgets only if the widget has a valid sensor mapping.

The safest method is:

- create a `Number` or `Progress` widget
- choose a `Sensor preset`
- save the UI
- compile the theme

If a widget has no sensor mapping, live runtime data will not be displayed there.

**Русский**

Для новых тем live-значения датчиков будут приходить в виджеты только если у виджета настроен корректный sensor mapping.

Самый безопасный способ:

- создать `Number` или `Progress` виджет
- выбрать `Sensor preset`
- сохранить UI
- собрать тему

Если у виджета нет sensor mapping, live-runtime данные в нём отображаться не будут.

## 10. DateTime Notes / Замечания по DateTime

**English**

Date/time widgets are supported and should now render correctly in both vendor-derived and newly created themes after compilation.

When creating new themes:

- use `Add DateTime`
- set the desired `Date/time fmt`
- save the UI
- compile the theme

**Русский**

Виджеты даты/времени поддерживаются и после сборки должны теперь корректно отображаться как в vendor-derived темах, так и в новых пользовательских темах.

При создании новых тем:

- используйте `Add DateTime`
- задавайте нужный `Date/time fmt`
- сохраняйте UI
- собирайте тему

## 11. Practical Recommendations / Практические рекомендации

**English**

- Use `Save UI` for normal edits to the current theme
- Use `Save As` before major experiments
- Use `Compile DAT` when you want a rebuild without immediate upload
- Use `Compile+Upload` when tuning the theme directly on the real monitor
- Prefer `Sensor preset` instead of entering raw sensor fields manually

**Русский**

- Для обычного редактирования текущей темы используйте `Save UI`
- Перед большими экспериментами используйте `Save As`
- Используйте `Compile DAT`, если хотите пересобрать тему без немедленной загрузки
- Используйте `Compile+Upload`, если настраиваете тему сразу под реальный монитор
- Для датчиков лучше использовать `Sensor preset`, а не вводить sensor-поля вручную
