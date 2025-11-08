-- Таблица для сырых данных из источников (SCADA/ERP)
CREATE TABLE IF NOT EXISTS raw_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    installation_id VARCHAR(50),
    power_kwh FLOAT NOT NULL,
    load_percent FLOAT,
    temperature FLOAT,
    pressure FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для очищенных и нормализованных данных
CREATE TABLE IF NOT EXISTS clean_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    installation_id VARCHAR(50),
    power_kwh FLOAT NOT NULL,
    load_percent FLOAT,
    temperature FLOAT,
    pressure FLOAT,
    efficiency FLOAT,
    specific_consumption FLOAT,
    is_outlier BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для прогнозных данных
CREATE TABLE IF NOT EXISTS forecast (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    predicted_kwh FLOAT NOT NULL,
    confidence_lower FLOAT,
    confidence_upper FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для обнаруженных аномалий
CREATE TABLE IF NOT EXISTS anomalies (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    power_kwh FLOAT NOT NULL,
    excess_kwh FLOAT,
    cause VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_raw_data_timestamp ON raw_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_clean_data_timestamp ON clean_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_forecast_timestamp ON forecast(timestamp);
CREATE INDEX IF NOT EXISTS idx_anomalies_timestamp ON anomalies(timestamp);