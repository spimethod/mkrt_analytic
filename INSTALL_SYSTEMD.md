# Установка Market Analysis Bot как systemd службы

## Шаги установки

### 1. Подготовка файлов

1. Скопируйте проект в `/opt/market-analysis-bot/`:

```bash
sudo mkdir -p /opt/market-analysis-bot
sudo cp -r * /opt/market-analysis-bot/
sudo chown -R your_username:your_username /opt/market-analysis-bot
```

2. Установите зависимости:

```bash
cd /opt/market-analysis-bot
pip3 install -r requirements.txt
```

### 2. Настройка systemd службы

1. Отредактируйте файл `market-analysis-bot.service`:

```bash
sudo nano /opt/market-analysis-bot/market-analysis-bot.service
```

2. Измените следующие строки:

   - `User=your_username` → `User=ваш_пользователь`
   - `WorkingDirectory=/path/to/mkrt_analytic` → `WorkingDirectory=/opt/market-analysis-bot`
   - `ExecStart=/usr/bin/python3 /path/to/mkrt_analytic/main.py` → `ExecStart=/usr/bin/python3 /opt/market-analysis-bot/main.py`

3. Скопируйте файл службы:

```bash
sudo cp /opt/market-analysis-bot/market-analysis-bot.service /etc/systemd/system/
```

### 3. Настройка переменных окружения

1. Создайте файл `.env` в директории проекта:

```bash
cp /opt/market-analysis-bot/env_example.txt /opt/market-analysis-bot/.env
nano /opt/market-analysis-bot/.env
```

2. Заполните все необходимые переменные в файле `.env`

### 4. Создание базы данных

1. Создайте базу данных:

```bash
sudo -u postgres createdb mkrt_analytic
```

2. Выполните SQL скрипт:

```bash
sudo -u postgres psql -d mkrt_analytic -f /opt/market-analysis-bot/create_tables.sql
```

### 5. Запуск службы

1. Перезагрузите systemd:

```bash
sudo systemctl daemon-reload
```

2. Включите автозапуск:

```bash
sudo systemctl enable market-analysis-bot.service
```

3. Запустите службу:

```bash
sudo systemctl start market-analysis-bot.service
```

### 6. Проверка работы

1. Проверьте статус:

```bash
sudo systemctl status market-analysis-bot.service
```

2. Просмотрите логи:

```bash
sudo journalctl -u market-analysis-bot.service -f
```

## Управление службой

### Запуск/остановка

```bash
sudo systemctl start market-analysis-bot.service
sudo systemctl stop market-analysis-bot.service
sudo systemctl restart market-analysis-bot.service
```

### Просмотр логов

```bash
# Все логи
sudo journalctl -u market-analysis-bot.service

# Логи в реальном времени
sudo journalctl -u market-analysis-bot.service -f

# Логи за последний час
sudo journalctl -u market-analysis-bot.service --since "1 hour ago"
```

### Отключение автозапуска

```bash
sudo systemctl disable market-analysis-bot.service
```

## Устранение неполадок

### Проверка подключений

```bash
cd /opt/market-analysis-bot
python3 test_connection.py
```

### Проверка прав доступа

```bash
ls -la /opt/market-analysis-bot/
sudo chown -R your_username:your_username /opt/market-analysis-bot
```

### Проверка переменных окружения

```bash
sudo systemctl show market-analysis-bot.service --property=Environment
```

## Обновление бота

1. Остановите службу:

```bash
sudo systemctl stop market-analysis-bot.service
```

2. Обновите файлы:

```bash
sudo cp -r new_files/* /opt/market-analysis-bot/
```

3. Перезапустите службу:

```bash
sudo systemctl start market-analysis-bot.service
```
