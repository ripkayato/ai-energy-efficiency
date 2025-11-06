import json
import pandas as pd
from sqlalchemy import create_engine, text
import time

print("ETL: загрузка сырых данных...")

# Читаем из общего тома
try:
    with open("/shared/raw_data.json") as f:
        data = json.load(f)
except FileNotFoundError:
    print("Ошибка: /shared/raw_data.json не найден!")
    exit(1)

# Преобразуем в DataFrame
df = pd.DataFrame(data)

# Очистка (на всякий случай)
df = df.dropna()
# Проверка деления на ноль
df = df[df['load_percent'] != 0]  # Удаляем записи с нулевой загрузкой
df['efficiency'] = df['power_kwh'] / df['load_percent']

# Retry логика для подключения к БД
max_retries = 10
retry_delay = 2
engine = None

for attempt in range(max_retries):
    try:
        engine = create_engine('postgresql://user:pass@database:5432/energy')
        # Проверяем подключение
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Подключение к БД установлено")
        break
    except Exception as e:
        if attempt < max_retries - 1:
            print(f"Попытка подключения {attempt + 1}/{max_retries} не удалась: {e}. Повтор через {retry_delay}с...")
            time.sleep(retry_delay)
        else:
            print(f"Ошибка подключения к БД после {max_retries} попыток: {e}")
            exit(1)

# Загрузка в таблицу measurements
df.to_sql('measurements', engine, if_exists='append', index=False)

print("ETL: данные загружены в БД")