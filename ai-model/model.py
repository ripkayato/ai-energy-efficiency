import pandas as pd
from prophet import Prophet
from sqlalchemy import create_engine

print("AI: обучение модели...")
engine = create_engine('postgresql://user:pass@database:5432/energy')
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
forecast[['ds', 'yhat']].tail(7).to_json("forecast.json", orient="records")
print("Прогноз сохранён: forecast.json")