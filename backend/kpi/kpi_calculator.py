"""
Модуль расчета KPI: энергоэффективность, перерасход, экономический эффект
Вычисляет EnPI (удельное потребление энергии), перерасход, экономию в рублях
"""
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from typing import Dict, List
from datetime import datetime, timedelta


class KPICalculator:
    def __init__(self, db_url: str = "postgresql://user:pass@database:5432/energy", 
                 energy_price_per_kwh: float = 5.0):
        """
        Инициализация калькулятора KPI
        energy_price_per_kwh: цена за кВт·ч в рублях (по умолчанию 5 руб/кВт·ч)
        """
        self.db_url = db_url
        self.engine = None
        self.energy_price_per_kwh = energy_price_per_kwh
        self._connect_db()

    def _connect_db(self, max_retries: int = 10, retry_delay: int = 2):
        """Подключение к БД с повторными попытками"""
        import time
        for attempt in range(max_retries):
            try:
                self.engine = create_engine(self.db_url)
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                print("KPI: Подключение к БД установлено")
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"KPI: Попытка подключения {attempt + 1}/{max_retries} не удалась: {e}")
                    time.sleep(retry_delay)
                else:
                    print(f"KPI: Ошибка подключения к БД: {e}")
                    return False
        return False

    def calculate_enpi(self, period_days: int = 30) -> Dict:
        """
        Расчёт EnPI (Energy Performance Indicator) - удельное потребление энергии
        EnPI = Энергопотребление / Производительность (кВт·ч на единицу продукции)
        В нашем случае: кВт·ч / загрузка %
        """
        if self.engine is None:
            return {}
        
        try:
            query = f"""
                SELECT 
                    AVG(power_kwh) as avg_power_kwh,
                    AVG(load_percent) as avg_load_percent,
                    COUNT(*) as record_count
                FROM clean_data
                WHERE timestamp >= NOW() - INTERVAL '{period_days} days'
            """
            
            result = pd.read_sql(query, self.engine)
            if result.empty or result['record_count'].iloc[0] == 0:
                return {}
            
            avg_power = result['avg_power_kwh'].iloc[0]
            avg_load = result['avg_load_percent'].iloc[0]
            
            if avg_load > 0:
                enpi = avg_power / avg_load  # кВт·ч на % загрузки
            else:
                enpi = 0
            
            # Базовое значение EnPI (можно взять из исторических данных или настроить)
            baseline_enpi = enpi * 1.05  # Пример: базовое значение на 5% выше текущего
            
            # Отклонение от базового значения
            enpi_deviation_percent = ((enpi - baseline_enpi) / baseline_enpi) * 100 if baseline_enpi > 0 else 0
            
            return {
                "enpi": round(enpi, 4),
                "baseline_enpi": round(baseline_enpi, 4),
                "deviation_percent": round(enpi_deviation_percent, 2),
                "period_days": period_days,
                "avg_power_kwh": round(avg_power, 2),
                "avg_load_percent": round(avg_load, 2)
            }
        except Exception as e:
            print(f"KPI: Ошибка расчёта EnPI: {e}")
            return {}

    def calculate_excess_consumption(self, period_days: int = 30) -> Dict:
        """
        Расчёт перерасхода энергии (в кВт·ч и %)
        Сравнивает фактическое потребление с нормативным/прогнозным
        """
        if self.engine is None:
            return {}
        
        try:
            # Получаем фактические данные
            actual_query = f"""
                SELECT 
                    SUM(power_kwh) as total_power_kwh,
                    AVG(power_kwh) as avg_power_kwh,
                    COUNT(*) as record_count
                FROM clean_data
                WHERE timestamp >= NOW() - INTERVAL '{period_days} days'
            """
            actual = pd.read_sql(actual_query, self.engine)
            
            # Получаем прогнозные данные (если есть)
            forecast_query = f"""
                SELECT 
                    SUM(predicted_kwh) as total_predicted_kwh,
                    AVG(predicted_kwh) as avg_predicted_kwh
                FROM forecast
                WHERE timestamp >= NOW() - INTERVAL '{period_days} days'
            """
            forecast = pd.read_sql(forecast_query, self.engine)
            
            if actual.empty:
                return {}
            
            total_actual = actual['total_power_kwh'].iloc[0] or 0
            avg_actual = actual['avg_power_kwh'].iloc[0] or 0
            
            # Если есть прогноз, используем его как норматив
            if not forecast.empty and forecast['total_predicted_kwh'].iloc[0]:
                total_predicted = forecast['total_predicted_kwh'].iloc[0]
                excess_kwh = total_actual - total_predicted
                excess_percent = (excess_kwh / total_predicted * 100) if total_predicted > 0 else 0
            else:
                # Иначе используем среднее значение как базовое
                # Предполагаем, что норматив = среднее значение за период
                baseline_kwh = avg_actual * actual['record_count'].iloc[0]
                excess_kwh = total_actual - baseline_kwh
                excess_percent = (excess_kwh / baseline_kwh * 100) if baseline_kwh > 0 else 0
            
            # Получаем перерасход из таблицы аномалий
            anomalies_query = f"""
                SELECT SUM(excess_kwh) as total_excess_kwh
                FROM anomalies
                WHERE timestamp >= NOW() - INTERVAL '{period_days} days'
            """
            anomalies = pd.read_sql(anomalies_query, self.engine)
            anomalies_excess = anomalies['total_excess_kwh'].iloc[0] or 0
            
            return {
                "total_consumption_kwh": round(total_actual, 2),
                "excess_kwh": round(excess_kwh, 2),
                "excess_percent": round(excess_percent, 2),
                "anomalies_excess_kwh": round(anomalies_excess, 2),
                "period_days": period_days
            }
        except Exception as e:
            print(f"KPI: Ошибка расчёта перерасхода: {e}")
            return {}

    def calculate_economic_effect(self, optimization_percent: float = 1.0, 
                                  period_days: int = 30) -> Dict:
        """
        Расчёт экономического эффекта от оптимизации
        optimization_percent: процент снижения перерасхода (1-5%)
        """
        excess_data = self.calculate_excess_consumption(period_days)
        if not excess_data or excess_data.get('excess_kwh', 0) <= 0:
            return {
                "savings_kwh": 0,
                "savings_rub": 0,
                "optimization_percent": optimization_percent,
                "period_days": period_days
            }
        
        excess_kwh = excess_data['excess_kwh']
        
        # Потенциальная экономия при оптимизации
        savings_kwh = excess_kwh * (optimization_percent / 100)
        savings_rub = savings_kwh * self.energy_price_per_kwh
        
        # Годовая экстраполяция
        days_per_year = 365
        annual_savings_kwh = savings_kwh * (days_per_year / period_days)
        annual_savings_rub = annual_savings_kwh * self.energy_price_per_kwh
        
        return {
            "savings_kwh": round(savings_kwh, 2),
            "savings_rub": round(savings_rub, 2),
            "annual_savings_kwh": round(annual_savings_kwh, 2),
            "annual_savings_rub": round(annual_savings_rub, 2),
            "optimization_percent": optimization_percent,
            "period_days": period_days,
            "energy_price_per_kwh": self.energy_price_per_kwh
        }

    def calculate_efficiency(self, period_days: int = 30) -> Dict:
        """
        Расчёт КПД (коэффициент полезного действия)
        КПД = (Полезная работа / Затраченная энергия) * 100%
        В нашем случае: (загрузка / потребление) * коэффициент
        """
        if self.engine is None:
            return {}
        
        try:
            query = f"""
                SELECT 
                    AVG(efficiency) as avg_efficiency,
                    MIN(efficiency) as min_efficiency,
                    MAX(efficiency) as max_efficiency,
                    AVG(power_kwh) as avg_power_kwh,
                    AVG(load_percent) as avg_load_percent
                FROM clean_data
                WHERE timestamp >= NOW() - INTERVAL '{period_days} days'
            """
            
            result = pd.read_sql(query, self.engine)
            if result.empty:
                return {}
            
            return {
                "avg_efficiency": round(result['avg_efficiency'].iloc[0] or 0, 2),
                "min_efficiency": round(result['min_efficiency'].iloc[0] or 0, 2),
                "max_efficiency": round(result['max_efficiency'].iloc[0] or 0, 2),
                "period_days": period_days
            }
        except Exception as e:
            print(f"KPI: Ошибка расчёта КПД: {e}")
            return {}

    def get_all_kpis(self, period_days: int = 30, optimization_percent: float = 1.0) -> Dict:
        """Получение всех KPI за период"""
        return {
            "enpi": self.calculate_enpi(period_days),
            "excess_consumption": self.calculate_excess_consumption(period_days),
            "efficiency": self.calculate_efficiency(period_days),
            "economic_effect": self.calculate_economic_effect(optimization_percent, period_days),
            "period_days": period_days,
            "timestamp": datetime.now().isoformat()
        }

