# Codex Balance Widget

Небольшой Windows-виджет для просмотра лимитов Codex Usage. Виджет открывает страницу
`https://chatgpt.com/codex/cloud/settings/analytics#usage` через установленный Google
Chrome, считывает видимый текст и показывает остаток лимита в отдельном окне.

## Требования

- Windows
- Python 3.10 или новее
- Google Chrome
- доступ к странице Codex Usage в аккаунте ChatGPT

## Установка

1. Запустите:

   ```bat
   install.bat
   ```

2. Дождитесь установки Python-библиотеки Playwright.

Скачивать отдельный Playwright Chromium не нужно: приложение использует системный
Google Chrome.

## Запуск

Запустите:

```bat
run.bat
```

`run.bat` вызывает `run_hidden.vbs`, а тот запускает приложение без лишнего окна
консоли. При первом старте откроется Chrome: войдите в ChatGPT вручную и закройте
окно после успешной авторизации. Последующие обновления выполняются в фоне.

Для отладки можно запустить основной файл напрямую:

```bat
python codex_balance_widget_chrome.py
```

## Локальный профиль Chrome

Приложение не использует основной профиль Chrome. Оно создаёт отдельную локальную
папку:

```text
codex_chrome_profile
```

В ней хранится отдельная сессия ChatGPT для виджета. Папка исключена из Git через
`.gitignore`: не публикуйте её и не передавайте другим людям.

## Настройки

Через кнопку настроек в окне виджета можно изменить:

- положение и размер окна
- режим отображения поверх других окон
- отображение графика расхода лимита
- частоту обновления

Настройки сохраняются локально в `codex_balance_widget_settings.json`. История для
графика хранится в `codex_balance_history.json`. Оба файла исключены из Git.

Частота обновления по умолчанию задаётся в `codex_balance_widget_chrome.py`:

```python
REFRESH_SECONDS = 300
```

## Если Chrome не найден

Укажите путь через переменную окружения `CHROME_PATH`.

Пример для текущего окна CMD:

```bat
set CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
python codex_balance_widget_chrome.py
```

Обычно Chrome установлен в одной из папок:

```text
C:\Program Files\Google\Chrome\Application\chrome.exe
C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
```

## Диагностика

Если виджет не запускается, проверьте файл `widget_launch.log`. Он создаётся рядом
со скриптами и исключён из Git.

Если скрытый запуск не находит Python, проверьте путь `pythonwPath` в
`run_hidden.vbs`. В скрипте есть запасной запуск через `pyw.exe -3`.

## Ограничения

Это не официальный API. Виджет читает видимый текст страницы Codex Usage. Если
интерфейс страницы изменится, может потребоваться обновить функцию `parse_balance()`.
