import json
import pandas as pd
from sqlalchemy import create_engine

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

# Подключение к БД
engine = create_engine('postgresql://user:pass@database:5432/energy')

# Загрузка в таблицу measurements
df.to_sql('measurements', engine, if_exists='append', index=False)

print("ETL: данные загружены в БД")