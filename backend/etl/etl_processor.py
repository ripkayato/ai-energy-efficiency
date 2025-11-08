"""
ETL модуль: обработка сырых данных из источников (SCADA/ERP)
Извлечение, нормализация, удаление выбросов, расчёт удельных показателей
"""
import json
import pandas as pd
from sqlalchemy import create_engine, text
import time
from typing import Dict, List


class ETLProcessor:
    def __init__(self, db_url: str = "postgresql://user:pass@database:5432/energy"):
        self.db_url = db_url
        self.engine = None
        self._connect_db()

    def _connect_db(self, max_retries: int = 10, retry_delay: int = 2):
        """Подключение к БД с повторными попытками"""
        for attempt in range(max_retries):
            try:
                self.engine = create_engine(self.db_url)
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                print("ETL: Подключение к БД установлено")
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"ETL: Попытка подключения {attempt + 1}/{max_retries} не удалась: {e}. Повтор через {retry_delay}с...")
                    time.sleep(retry_delay)
                else:
                    print(f"ETL: Ошибка подключения к БД после {max_retries} попыток: {e}")
                    return False
        return False

    def load_raw_data(self, file_path: str = "/shared/raw_data.json") -> pd.DataFrame:
        """Загрузка сырых данных из файла"""
        try:
            with open(file_path) as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            print(f"ETL: Загружено {len(df)} записей из {file_path}")
            return df
        except FileNotFoundError:
            print(f"ETL: Ошибка: {file_path} не найден!")
            return pd.DataFrame()
        except Exception as e:
            print(f"ETL: Ошибка чтения файла: {e}")
            return pd.DataFrame()

    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Нормализация данных: очистка, удаление выбросов, расчёт метрик"""
        if df.empty:
            return df

        # Удаление пустых значений
        df = df.dropna()
        
        # Проверка и фильтрация некорректных значений
        if 'load_percent' in df.columns:
            df = df[df['load_percent'] > 0]  # Удаляем записи с нулевой загрузкой
            df = df[df['load_percent'] <= 100]  # Удаляем некорректные значения > 100%
        
        if 'power_kwh' in df.columns:
            df = df[df['power_kwh'] > 0]  # Удаляем отрицательные или нулевые значения
        
        # Преобразование timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Расчёт удельных показателей
        if 'power_kwh' in df.columns and 'load_percent' in df.columns:
            # КПД (эффективность использования энергии)
            df['efficiency'] = df['load_percent'] / df['power_kwh'] * 100
        
        # Удельное потребление (кВт·ч на единицу загрузки)
        if 'power_kwh' in df.columns and 'load_percent' in df.columns:
            df['specific_consumption'] = df['power_kwh'] / df['load_percent']
        
        print(f"ETL: Нормализовано {len(df)} записей")
        return df

    def detect_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Обнаружение выбросов методом IQR"""
        if df.empty or 'power_kwh' not in df.columns:
            return df
        
        Q1 = df['power_kwh'].quantile(0.25)
        Q3 = df['power_kwh'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Помечаем выбросы, но не удаляем их (для анализа аномалий)
        df['is_outlier'] = (df['power_kwh'] < lower_bound) | (df['power_kwh'] > upper_bound)
        
        return df

    def save_to_raw_data_table(self, df: pd.DataFrame) -> bool:
        """Сохранение сырых данных в таблицу raw_data"""
        if self.engine is None or df.empty:
            return False
        
        try:
            # Переименовываем колонки для соответствия схеме БД
            df_to_save = df.copy()
            if 'temp' in df_to_save.columns:
                df_to_save = df_to_save.rename(columns={'temp': 'temperature'})
            
            # Сохраняем только нужные колонки
            columns_to_save = ['timestamp', 'power_kwh', 'load_percent', 'temperature']
            if 'installation_id' in df_to_save.columns:
                columns_to_save.append('installation_id')
            
            df_to_save = df_to_save[[col for col in columns_to_save if col in df_to_save.columns]]
            
            df_to_save.to_sql('raw_data', self.engine, if_exists='append', index=False)
            print(f"ETL: Сохранено {len(df_to_save)} записей в таблицу raw_data")
            return True
        except Exception as e:
            print(f"ETL: Ошибка сохранения в raw_data: {e}")
            return False

    def save_to_clean_data_table(self, df: pd.DataFrame) -> bool:
        """Сохранение очищенных данных в таблицу clean_data"""
        if self.engine is None or df.empty:
            return False
        
        try:
            # Подготовка данных для clean_data
            df_clean = df.copy()
            if 'temp' in df_clean.columns:
                df_clean = df_clean.rename(columns={'temp': 'temperature'})
            
            # Выбираем колонки для clean_data
            columns_for_clean = ['timestamp', 'power_kwh', 'load_percent', 'temperature', 
                                'efficiency', 'specific_consumption']
            if 'installation_id' in df_clean.columns:
                columns_for_clean.append('installation_id')
            
            df_clean = df_clean[[col for col in columns_for_clean if col in df_clean.columns]]
            
            df_clean.to_sql('clean_data', self.engine, if_exists='append', index=False)
            print(f"ETL: Сохранено {len(df_clean)} записей в таблицу clean_data")
            return True
        except Exception as e:
            print(f"ETL: Ошибка сохранения в clean_data: {e}")
            return False

    def process(self, file_path: str = "/shared/raw_data.json") -> Dict:
        """Основной метод обработки данных"""
        print("ETL: Начало обработки данных...")
        
        # Загрузка сырых данных
        raw_df = self.load_raw_data(file_path)
        if raw_df.empty:
            return {"status": "error", "message": "Не удалось загрузить сырые данные"}
        
        # Сохранение сырых данных
        self.save_to_raw_data_table(raw_df)
        
        # Нормализация
        clean_df = self.normalize_data(raw_df)
        if clean_df.empty:
            return {"status": "error", "message": "Не удалось нормализовать данные"}
        
        # Обнаружение выбросов
        clean_df = self.detect_outliers(clean_df)
        
        # Сохранение очищенных данных
        self.save_to_clean_data_table(clean_df)
        
        print("ETL: Обработка данных завершена успешно")
        return {
            "status": "success",
            "raw_records": len(raw_df),
            "clean_records": len(clean_df)
        }

