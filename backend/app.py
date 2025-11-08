"""
Главный файл Backend сервиса
Объединяет модули: ETL, AI, KPI, Auth
"""
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import uvicorn
import os

# Импорты модулей
import sys

# Добавляем текущую директорию в путь для импорта модулей
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from etl.etl_processor import ETLProcessor
from ai.ai_model import AIModel
from kpi.kpi_calculator import KPICalculator
from auth.auth import (
    get_auth_module, get_current_user as auth_get_current_user, require_admin, 
    Token, User, AuthModule
)
from fastapi.security import OAuth2PasswordRequestForm

# Конфигурация
DB_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@database:5432/energy")

# Создание FastAPI приложения
app = FastAPI(
    title="Energy Efficiency Backend API",
    description="Backend сервис для системы оптимизации энергоэффективности НПЗ",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация модулей
etl_processor = ETLProcessor(DB_URL)
ai_model = AIModel(DB_URL)
kpi_calculator = KPICalculator(DB_URL)
auth_module = get_auth_module()


# ==================== Эндпоинты аутентификации ====================

@app.post("/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Аутентификация пользователя"""
    return await auth_module.login(form_data)


@app.post("/auth/register")
async def register(
    username: str,
    email: str,
    password: str,
    role: str = "user"
):
    """Регистрация нового пользователя"""
    return await auth_module.register(username, email, password, role)


@app.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(auth_get_current_user)):
    """Получить информацию о текущем пользователе"""
    return current_user


# ==================== Эндпоинты ETL ====================

@app.post("/etl/process")
async def process_etl(
    file_path: str = "/shared/raw_data.json",
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(auth_get_current_user)
):
    """Запуск ETL обработки данных"""
    def run_etl():
        return etl_processor.process(file_path)
    
    if background_tasks:
        background_tasks.add_task(run_etl)
        return {"status": "processing", "message": "ETL обработка запущена в фоне"}
    else:
        result = run_etl()
        return result


@app.get("/etl/status")
async def get_etl_status(current_user: User = Depends(auth_get_current_user)):
    """Получить статус ETL обработки"""
    # Здесь можно добавить логику проверки статуса
    return {"status": "ready"}


# ==================== Эндпоинты AI ====================

@app.post("/ai/analyze")
async def run_ai_analysis(
    forecast_periods: int = 7,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(auth_get_current_user)
):
    """Запуск AI анализа: обучение, прогноз, обнаружение аномалий"""
    def run_analysis():
        return ai_model.run_full_analysis(forecast_periods)
    
    if background_tasks:
        background_tasks.add_task(run_analysis)
        return {"status": "processing", "message": "AI анализ запущен в фоне"}
    else:
        result = run_analysis()
        return result


@app.get("/ai/forecast")
async def get_forecast(
    periods: int = 7,
    current_user: User = Depends(auth_get_current_user)
):
    """Получить прогноз энергопотребления"""
    try:
        # Загружаем данные для обучения
        training_data = ai_model.load_training_data()
        if training_data.empty:
            return {"error": "Недостаточно данных для прогноза"}
        
        # Обучаем модель
        ai_model.train_model(training_data)
        
        # Получаем прогноз
        forecast = ai_model.predict(periods=periods)
        if forecast.empty:
            return {"error": "Ошибка генерации прогноза"}
        
        return {
            "status": "success",
            "forecast": forecast.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/anomalies")
async def get_anomalies(
    days: int = 30,
    current_user: User = Depends(auth_get_current_user)
):
    """Получить обнаруженные аномалии"""
    try:
        training_data = ai_model.load_training_data(days=days)
        if training_data.empty:
            return {"anomalies": []}
        
        anomalies = ai_model.detect_anomalies(training_data)
        return {
            "status": "success",
            "anomalies": anomalies.to_dict(orient="records") if not anomalies.empty else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Эндпоинты KPI ====================

@app.get("/kpi/enpi")
async def get_enpi(
    period_days: int = 30,
    current_user: User = Depends(auth_get_current_user)
):
    """Получить EnPI (удельное потребление энергии)"""
    return kpi_calculator.calculate_enpi(period_days)


@app.get("/kpi/excess")
async def get_excess_consumption(
    period_days: int = 30,
    current_user: User = Depends(auth_get_current_user)
):
    """Получить перерасход энергии"""
    return kpi_calculator.calculate_excess_consumption(period_days)


@app.get("/kpi/efficiency")
async def get_efficiency(
    period_days: int = 30,
    current_user: User = Depends(auth_get_current_user)
):
    """Получить КПД"""
    return kpi_calculator.calculate_efficiency(period_days)


@app.get("/kpi/economic")
async def get_economic_effect(
    optimization_percent: float = 1.0,
    period_days: int = 30,
    current_user: User = Depends(auth_get_current_user)
):
    """Получить экономический эффект от оптимизации"""
    return kpi_calculator.calculate_economic_effect(optimization_percent, period_days)


@app.get("/kpi/all")
async def get_all_kpis(
    period_days: int = 30,
    optimization_percent: float = 1.0,
    current_user: User = Depends(auth_get_current_user)
):
    """Получить все KPI"""
    return kpi_calculator.get_all_kpis(period_days, optimization_percent)


# ==================== Общие эндпоинты ====================

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "Energy Efficiency Backend API",
        "version": "1.0.0",
        "modules": ["etl", "ai", "kpi", "auth"]
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "database": "connected" if etl_processor.engine else "disconnected"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

