print("Генерация данных...")
import pandas as pd
import numpy as np

data = {"power_kwh": np.random.randint(1400, 1800, 10)}
df = pd.DataFrame(data)
df.to_csv("data.csv", index=False)
print("data.csv создан!")