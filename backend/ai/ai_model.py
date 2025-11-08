"""
AI модуль: анализ данных, прогнозирование, выявление аномалий
Использует Prophet/ARIMA/Scikit-learn для прогноза энергопотребления
"""
import pandas as pd
import numpy as np
from prophet import Prophet
from sqlalchemy import create_engine, text
import time
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import json


class AIModel:
    def __init__(self, db_url: str = "postgresql://user:pass@database:5432/energy"):
        self.db_url = db_url
        self.engine = None
        self.model = None
        self._connect_db()

    def _connect_db(self, max_retries: int = 10, retry_delay: int = 2):
        """Подключение к БД с повторными попытками"""
        for attempt in range(max_retries):
            try:
                self.engine = create_engine(self.db_url)
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                print("AI: Подключение к БД установлено")
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"AI: Попытка подключения {attempt + 1}/{max_retries} не удалась: {e}. Повтор через {retry_delay}с...")
                    time.sleep(retry_delay)
                else:
                    print(f"AI: Ошибка подключения к БД после {max_retries} попыток: {e}")
                    return False
        return False

    def load_training_data(self, days: int = 30) -> pd.DataFrame:
        """Загрузка данных для обучения из clean_data"""
        if self.engine is None:
            return pd.DataFrame()
        
        try:
            query = f"""
                SELECT timestamp as ds, power_kwh as y, load_percent, temperature
                FROM clean_data
                WHERE timestamp >= NOW() - INTERVAL '{days} days'
                ORDER BY timestamp
            """
            df = pd.read_sql(query, self.engine)
            if 'ds' in df.columns:
                df['ds'] = pd.to_datetime(df['ds'])
            print(f"AI: Загружено {len(df)} записей для обучения")
            return df
        except Exception as e:
            print(f"AI: Ошибка загрузки данных: {e}")
            return pd.DataFrame()

    def train_model(self, df: pd.DataFrame) -> bool:
        """Обучение модели Prophet"""
        if df.empty or 'ds' not in df.columns or 'y' not in df.columns:
            print("AI: Недостаточно данных для обучения")
            return False
        
        try:
            # Подготовка данных для Prophet
            prophet_df = df[['ds', 'y']].copy()
            
            # Добавляем регрессоры если есть
            if 'load_percent' in df.columns:
                prophet_df['load_percent'] = df['load_percent']
            
            if 'temperature' in df.columns:
                prophet_df['temperature'] = df['temperature']
            
            # Создаём и обучаем модель
            self.model = Prophet()
            
            # Добавляем регрессоры
            if 'load_percent' in prophet_df.columns:
                self.model.add_regressor('load_percent')
            if 'temperature' in prophet_df.columns:
                self.model.add_regressor('temperature')
            
            self.model.fit(prophet_df[['ds', 'y'] + [col for col in ['load_percent', 'temperature'] if col in prophet_df.columns]])
            
            print("AI: Модель обучена успешно")
            return True
        except Exception as e:
            print(f"AI: Ошибка обучения модели: {e}")
            return False

    def predict(self, periods: int = 7, freq: str = 'D') -> pd.DataFrame:
        """Прогнозирование на указанный период"""
        if self.model is None:
            print("AI: Модель не обучена")
            return pd.DataFrame()
        
        try:
            future = self.model.make_future_dataframe(periods=periods, freq=freq)
            forecast = self.model.predict(future)
            
            # Берём только прогнозные значения
            forecast_result = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
            print(f"AI: Сгенерирован прогноз на {periods} периодов")
            return forecast_result
        except Exception as e:
            print(f"AI: Ошибка прогнозирования: {e}")
            return pd.DataFrame()

    def detect_anomalies(self, df: pd.DataFrame, threshold_std: float = 2.0) -> pd.DataFrame:
        """Выявление аномалий в данных"""
        if df.empty:
            return pd.DataFrame()
        
        # Определяем колонку с энергопотреблением
        power_col = None
        if 'power_kwh' in df.columns:
            power_col = 'power_kwh'
        elif 'y' in df.columns:
            power_col = 'y'
        else:
            return pd.DataFrame()
        
        try:
            # Вычисляем статистики
            mean_power = df[power_col].mean()
            std_power = df[power_col].std()
            
            if std_power == 0:
                return pd.DataFrame()
            
            # Определяем аномалии (значения вне диапазона mean ± threshold_std * std)
            df = df.copy()
            df['is_anomaly'] = (df[power_col] < mean_power - threshold_std * std_power) | \
                              (df[power_col] > mean_power + threshold_std * std_power)
            
            # Вычисляем перерасход для аномалий
            df['excess_kwh'] = 0
            if power_col == 'y':
                df['power_kwh'] = df['y']
            
            df.loc[df['is_anomaly'] & (df[power_col] > mean_power), 'excess_kwh'] = \
                df.loc[df['is_anomaly'] & (df[power_col] > mean_power), power_col] - mean_power
            
            # Определяем причину аномалии
            df['cause'] = 'unknown'
            if 'load_percent' in df.columns:
                df.loc[df['is_anomaly'] & (df['load_percent'] > 95), 'cause'] = 'overload'
                df.loc[df['is_anomaly'] & (df['load_percent'] < 50) & (df[power_col] > mean_power), 'cause'] = 'low_efficiency'
            
            if 'efficiency' in df.columns:
                df.loc[df['is_anomaly'] & (df['efficiency'] < 80), 'cause'] = 'equipment_wear'
            elif df['is_anomaly'].any():
                # Если нет колонки efficiency, используем общую причину
                df.loc[df['is_anomaly'] & (df[power_col] > mean_power * 1.2), 'cause'] = 'high_consumption'
            
            # Преобразуем timestamp
            if 'ds' in df.columns:
                df['timestamp'] = pd.to_datetime(df['ds'])
            elif 'timestamp' not in df.columns:
                df['timestamp'] = pd.Timestamp.now()
            
            anomalies = df[df['is_anomaly']].copy()
            print(f"AI: Обнаружено {len(anomalies)} аномалий")
            
            return anomalies
        except Exception as e:
            print(f"AI: Ошибка обнаружения аномалий: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def save_forecast(self, forecast_df: pd.DataFrame) -> bool:
        """Сохранение прогноза в таблицу forecast"""
        if self.engine is None or forecast_df.empty:
            return False
        
        try:
            forecast_to_save = forecast_df.copy()
            forecast_to_save = forecast_to_save.rename(columns={
                'ds': 'timestamp',
                'yhat': 'predicted_kwh',
                'yhat_lower': 'confidence_lower',
                'yhat_upper': 'confidence_upper'
            })
            
            forecast_to_save.to_sql('forecast', self.engine, if_exists='append', index=False)
            print(f"AI: Сохранено {len(forecast_to_save)} прогнозных значений")
            return True
        except Exception as e:
            print(f"AI: Ошибка сохранения прогноза: {e}")
            return False

    def save_anomalies(self, anomalies_df: pd.DataFrame) -> bool:
        """Сохранение аномалий в таблицу anomalies"""
        if self.engine is None or anomalies_df.empty:
            return False
        
        try:
            anomalies_to_save = anomalies_df.copy()
            # Преобразуем ds в timestamp если нужно
            if 'timestamp' not in anomalies_to_save.columns and 'ds' in anomalies_to_save.columns:
                anomalies_to_save['timestamp'] = pd.to_datetime(anomalies_to_save['ds'])
            elif 'timestamp' in anomalies_to_save.columns:
                anomalies_to_save['timestamp'] = pd.to_datetime(anomalies_to_save['timestamp'])
            
            # Выбираем нужные колонки
            cols_to_save = ['timestamp', 'power_kwh']
            if 'excess_kwh' in anomalies_to_save.columns:
                cols_to_save.append('excess_kwh')
            if 'cause' in anomalies_to_save.columns:
                cols_to_save.append('cause')
            
            anomalies_to_save = anomalies_to_save[cols_to_save].copy()
            anomalies_to_save.to_sql('anomalies', self.engine, if_exists='append', index=False)
            print(f"AI: Сохранено {len(anomalies_to_save)} аномалий")
            return True
        except Exception as e:
            print(f"AI: Ошибка сохранения аномалий: {e}")
            return False

    def calculate_metrics(self, forecast_df: pd.DataFrame, actual_df: pd.DataFrame) -> Dict:
        """Расчёт метрик точности (MAPE, RMSE)"""
        if forecast_df.empty or actual_df.empty:
            return {}
        
        try:
            # Объединяем прогноз и факт по timestamp
            merged = pd.merge(
                forecast_df[['ds', 'yhat']],
                actual_df[['ds', 'y']],
                on='ds',
                how='inner'
            )
            
            if merged.empty:
                return {}
            
            # MAPE (Mean Absolute Percentage Error)
            mape = np.mean(np.abs((merged['y'] - merged['yhat']) / merged['y'])) * 100
            
            # RMSE (Root Mean Squared Error)
            rmse = np.sqrt(np.mean((merged['y'] - merged['yhat']) ** 2))
            
            return {
                "mape": round(mape, 2),
                "rmse": round(rmse, 2)
            }
        except Exception as e:
            print(f"AI: Ошибка расчёта метрик: {e}")
            return {}

    def run_full_analysis(self, forecast_periods: int = 7) -> Dict:
        """Полный цикл анализа: обучение, прогноз, обнаружение аномалий"""
        print("AI: Запуск полного анализа...")
        
        # Загрузка данных
        training_data = self.load_training_data()
        if training_data.empty:
            return {"status": "error", "message": "Недостаточно данных для обучения"}
        
        # Обучение модели
        if not self.train_model(training_data):
            return {"status": "error", "message": "Ошибка обучения модели"}
        
        # Прогнозирование
        forecast = self.predict(periods=forecast_periods)
        if forecast.empty:
            return {"status": "error", "message": "Ошибка прогнозирования"}
        
        # Сохранение прогноза
        self.save_forecast(forecast)
        
        # Обнаружение аномалий
        anomalies = self.detect_anomalies(training_data)
        if not anomalies.empty:
            self.save_anomalies(anomalies)
        
        # Расчёт метрик (если есть фактические данные для сравнения)
        metrics = self.calculate_metrics(forecast, training_data)
        
        print("AI: Анализ завершён успешно")
        return {
            "status": "success",
            "forecast_periods": forecast_periods,
            "anomalies_count": len(anomalies),
            "metrics": metrics,
            "forecast": forecast.to_dict(orient="records")
        }

