"""
Сервис генерации данных: создаёт псевдореалистичные временные ряды
Включает сценарии перерасхода: износ оборудования, неправильный режим работы, падение КПД
"""
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta


def generate_realistic_data(
    start_date: str = "2025-01-01",
    periods: int = 720,  # 30 дней по часам
    base_power: float = 1500,  # Базовое энергопотребление (кВт·ч)
    base_load: float = 80  # Базовая загрузка (%)
):
    """
    Генерация реалистичных данных с различными сценариями
    """
    # Создаём временной ряд
    timestamps = pd.date_range(start_date, periods=periods, freq="h")
    
    # Базовые значения
    power_kwh = []
    load_percent = []
    temperature = []
    
    # Сезонность (день/ночь, неделя)
    hour_of_day = np.array([t.hour for t in timestamps])
    day_of_week = np.array([t.weekday() for t in timestamps])
    day_of_period = np.arange(periods)
    
    # Базовый тренд износа оборудования (плавное повышение на 1-2% в неделю)
    wear_trend = 1 + (day_of_period / (24 * 7)) * 0.02  # 2% в неделю
    
    for i, ts in enumerate(timestamps):
        hour = hour_of_day[i]
        day = day_of_week[i]
        day_num = day_of_period[i]
        
        # Базовая загрузка с небольшими колебаниями
        base_load_value = base_load + np.random.normal(0, 5)
        base_load_value = np.clip(base_load_value, 50, 100)
        
        # Сезонные колебания (день/ночь)
        if 6 <= hour <= 22:  # День
            load_multiplier = 1.1
        else:  # Ночь
            load_multiplier = 0.9
        
        # Недельные колебания
        if day < 5:  # Будни
            load_multiplier *= 1.05
        else:  # Выходные
            load_multiplier *= 0.95
        
        load = base_load_value * load_multiplier
        load = np.clip(load, 50, 100)
        load_percent.append(load)
        
        # Энергопотребление зависит от загрузки
        # Базовое потребление с учётом износа
        power_base = base_power * wear_trend[i]
        
        # Нормальное потребление (пропорционально загрузке)
        power_normal = power_base * (load / 100) * (1 + np.random.normal(0, 0.05))
        
        # Сценарии перерасхода
        
        # 1. Износ оборудования: плавное повышение энергопотребления при стабильной нагрузке
        if day_num > 200:  # После ~8 дней начинается износ
            wear_factor = 1 + (day_num - 200) / 1000 * 0.15  # До 15% увеличения
            power_normal *= wear_factor
        
        # 2. Неправильный режим работы: аномальные пики (10-20% скачки)
        if np.random.random() < 0.05:  # 5% вероятность пика
            peak_factor = 1 + np.random.uniform(0.1, 0.2)
            power_normal *= peak_factor
        
        # 3. Падение КПД: постепенное снижение КПД (с 95% до 85%)
        if day_num > 100:
            efficiency_degradation = 1 - (day_num - 100) / 600 * 0.1  # До 10% снижения
            efficiency_degradation = max(0.85, efficiency_degradation)
            power_normal /= efficiency_degradation
        
        # 4. Дополнительные аномалии: климатические (температура)
        temp = 15 + 10 * np.sin(2 * np.pi * hour / 24) + np.random.normal(0, 3)
        temp = np.clip(temp, -10, 40)
        temperature.append(temp)
        
        # Влияние температуры на потребление (охлаждение/обогрев)
        if temp > 25 or temp < 5:
            temp_factor = 1 + abs(temp - 20) / 100 * 0.1
            power_normal *= temp_factor
        
        power_kwh.append(max(0, power_normal))
    
    # Создаём DataFrame
    df = pd.DataFrame({
        "timestamp": timestamps,
        "power_kwh": power_kwh,
        "load_percent": load_percent,
        "temp": temperature
    })
    
    # Добавляем installation_id (можно несколько установок)
    df["installation_id"] = "INST_001"
    
    return df


def add_anomalies(df: pd.DataFrame, anomaly_rate: float = 0.03):
    """
    Добавление дополнительных аномалий в данные
    """
    df = df.copy()
    n_anomalies = int(len(df) * anomaly_rate)
    
    # Выбираем случайные индексы для аномалий
    anomaly_indices = np.random.choice(df.index, size=n_anomalies, replace=False)
    
    for idx in anomaly_indices:
        anomaly_type = np.random.choice(["overload", "spike", "drop"])
        
        if anomaly_type == "overload":
            # Перегрузка: высокое потребление при высокой загрузке
            df.loc[idx, "load_percent"] = min(100, df.loc[idx, "load_percent"] * 1.2)
            df.loc[idx, "power_kwh"] *= 1.3
        
        elif anomaly_type == "spike":
            # Резкий скачок потребления
            df.loc[idx, "power_kwh"] *= 1.5
        
        elif anomaly_type == "drop":
            # Падение эффективности: низкая загрузка, но высокое потребление
            df.loc[idx, "load_percent"] *= 0.7
            df.loc[idx, "power_kwh"] *= 1.2
    
    return df


if __name__ == "__main__":
    print("Генерация сырых данных...")
    
    # Генерируем данные за последний месяц
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    df = generate_realistic_data(
        start_date=start_date.strftime("%Y-%m-%d"),
        periods=720  # 30 дней * 24 часа
    )
    
    # Добавляем аномалии
    df = add_anomalies(df, anomaly_rate=0.03)
    
    # Сохраняем в общий том /shared
    output_path = "/shared/raw_data.json"
    with open(output_path, "w") as f:
        json.dump(df.to_dict(orient="records"), f, default=str)
    
    print(f"Сырые данные сгенерированы: {output_path}")
    print(f"Записей: {len(df)}")
    print(f"Период: {df['timestamp'].min()} - {df['timestamp'].max()}")
    print(f"Среднее потребление: {df['power_kwh'].mean():.2f} кВт·ч")
    print(f"Максимальное потребление: {df['power_kwh'].max():.2f} кВт·ч")
