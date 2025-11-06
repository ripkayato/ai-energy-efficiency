import pandas as pd
from prophet import Prophet
from sqlalchemy import create_engine, text
import time

print("AI: обучение модели...")

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

try:
    df = pd.read_sql("SELECT timestamp as ds, power_kwh as y FROM measurements", engine)
except Exception as e:
    print(f"Ошибка чтения БД: {e}")
    exit(1)

if df.empty:
    print("Ошибка: таблица measurements пуста. Запустите сначала data-generator и etl.")
    exit(1)

m = Prophet()
m.fit(df)
future = m.make_future_dataframe(periods=7, freq='D')
forecast = m.predict(future)
forecast_path = "/app/forecast.json"
forecast[['ds', 'yhat']].tail(7).to_json(forecast_path, orient="records")
print(f"Прогноз сохранён: {forecast_path}")