CREATE TABLE IF NOT EXISTS measurements (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    power_kwh FLOAT,
    load_percent FLOAT,
    temp FLOAT,
    efficiency FLOAT
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);