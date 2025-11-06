CREATE TABLE IF NOT EXISTS measurements (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    power_kwh FLOAT,
    load_percent FLOAT,
    temp FLOAT,
    efficiency FLOAT
);