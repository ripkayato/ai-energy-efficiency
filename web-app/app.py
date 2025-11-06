import json
from fastapi import FastAPI
import uvicorn
import subprocess
import sys
import os

# === FastAPI ===
app = FastAPI()

@app.get("/forecast")
def get_forecast():
    try:
        # Используем путь из volume mount
        forecast_path = "/ai-model/forecast.json"
        with open(forecast_path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "Прогноз ещё не готов"}
    except Exception as e:
        return {"error": f"Ошибка чтения прогноза: {str(e)}"}

# Запуск Streamlit в отдельном процессе
def run_streamlit():
    subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", 
        "streamlit_app.py",
        "--server.port=8501", 
        "--server.address=0.0.0.0",
        "--server.headless=true"
    ])

# Запуск Streamlit в фоне
if __name__ == "__main__":
    # Запускаем Streamlit в отдельном процессе
    import threading
    threading.Thread(target=run_streamlit, daemon=True).start()
    # Запускаем FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8000)