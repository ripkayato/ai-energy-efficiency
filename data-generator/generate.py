import pandas as pd
import numpy as np
import json

print("Генерация сырых данных...")

# Создаём DataFrame с 100 записями
df = pd.DataFrame({
    "timestamp": pd.date_range("2025-01-01", periods=100, freq="h"),
    "power_kwh": np.random.randint(1400, 1800, 100),
    "load_percent": np.random.randint(70, 95, 100),
    "temp": np.random.randint(15, 30, 100)
})

# Сохраняем в общий том /shared
with open("/shared/raw_data.json", "w") as f:
    json.dump(df.to_dict(orient="records"), f, default=str)

print("Сырые данные сгенерированы: /shared/raw_data.json")