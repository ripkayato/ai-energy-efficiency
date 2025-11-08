"""
Веб-приложение для визуализации данных энергоэффективности
Дашборд с графиками, KPI, отчётами
"""
import streamlit as st
import requests
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Конфигурация
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
st.set_page_config(page_title="Система оптимизации энергоэффективности НПЗ", layout="wide")

# Функции для работы с API
@st.cache_data(ttl=60)
def get_forecast(periods=7):
    """Получить прогноз энергопотребления"""
    try:
        response = requests.get(f"{BACKEND_API_URL}/ai/forecast?periods={periods}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Ошибка получения прогноза: {e}")
        return None

@st.cache_data(ttl=60)
def get_kpis(period_days=30, optimization_percent=1.0):
    """Получить все KPI"""
    try:
        response = requests.get(
            f"{BACKEND_API_URL}/kpi/all?period_days={period_days}&optimization_percent={optimization_percent}",
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Ошибка получения KPI: {e}")
        return None

@st.cache_data(ttl=60)
def get_anomalies(days=30):
    """Получить аномалии"""
    try:
        response = requests.get(f"{BACKEND_API_URL}/ai/anomalies?days={days}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Ошибка получения аномалий: {e}")
        return None

# Главная страница
st.title("Система оптимизации энергоэффективности НПЗ")
st.markdown("---")

# Боковая панель для настроек
with st.sidebar:
    st.header("Настройки")
    period_days = st.slider("Период анализа (дни)", 7, 90, 30)
    optimization_percent = st.slider("Процент оптимизации", 0.5, 5.0, 1.0, 0.5)
    forecast_periods = st.slider("Период прогноза (дни)", 1, 14, 7)

# Вкладки
tab1, tab2, tab3, tab4 = st.tabs(["Дашборд", "Прогноз", "KPI", "Аномалии"])

# Вкладка 1: Дашборд
with tab1:
    st.header("Общий дашборд")
    
    # Получаем KPI
    kpis = get_kpis(period_days, optimization_percent)
    
    if kpis:
        # Метрики
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            enpi = kpis.get("enpi", {}).get("enpi", 0)
            st.metric("EnPI (удельное потребление)", f"{enpi:.4f}")
        
        with col2:
            excess = kpis.get("excess_consumption", {}).get("excess_percent", 0)
            st.metric("Перерасход", f"{excess:.2f}%")
        
        with col3:
            efficiency = kpis.get("efficiency", {}).get("avg_efficiency", 0)
            st.metric("Средний КПД", f"{efficiency:.2f}%")
        
        with col4:
            savings = kpis.get("economic_effect", {}).get("savings_rub", 0)
            st.metric("Экономия (руб)", f"{savings:,.0f}")
        
        # График энергопотребления
        st.subheader("Энергопотребление")
        forecast_data = get_forecast(forecast_periods)
        if forecast_data and "forecast" in forecast_data:
            df_forecast = pd.DataFrame(forecast_data["forecast"])
            df_forecast["ds"] = pd.to_datetime(df_forecast["ds"])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_forecast["ds"],
                y=df_forecast["yhat"],
                name="Прогноз",
                line=dict(color="blue")
            ))
            if "yhat_lower" in df_forecast.columns and "yhat_upper" in df_forecast.columns:
                fig.add_trace(go.Scatter(
                    x=df_forecast["ds"],
                    y=df_forecast["yhat_upper"],
                    name="Верхняя граница",
                    line=dict(color="lightblue", dash="dash"),
                    showlegend=False
                ))
                fig.add_trace(go.Scatter(
                    x=df_forecast["ds"],
                    y=df_forecast["yhat_lower"],
                    name="Нижняя граница",
                    line=dict(color="lightblue", dash="dash"),
                    fill="tonexty",
                    fillcolor="rgba(173, 216, 230, 0.2)"
                ))
            
            fig.update_layout(
                xaxis_title="Дата",
                yaxis_title="Энергопотребление (кВт·ч)",
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

# Вкладка 2: Прогноз
with tab2:
    st.header("Прогноз энергопотребления")
    
    forecast_data = get_forecast(forecast_periods)
    if forecast_data and "forecast" in forecast_data:
        df = pd.DataFrame(forecast_data["forecast"])
        df["ds"] = pd.to_datetime(df["ds"])
        
        st.dataframe(df)
        
        # График прогноза
        fig = px.line(df, x="ds", y="yhat", title="Прогноз энергопотребления")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Данные прогноза недоступны")

# Вкладка 3: KPI
with tab3:
    st.header("Ключевые показатели эффективности (KPI)")
    
    kpis = get_kpis(period_days, optimization_percent)
    
    if kpis:
        # EnPI
        st.subheader("EnPI (Energy Performance Indicator)")
        if "enpi" in kpis:
            enpi_data = kpis["enpi"]
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Текущий EnPI", f"{enpi_data.get('enpi', 0):.4f}")
                st.metric("Базовый EnPI", f"{enpi_data.get('baseline_enpi', 0):.4f}")
            with col2:
                deviation = enpi_data.get("deviation_percent", 0)
                st.metric("Отклонение", f"{deviation:.2f}%")
        
        # Перерасход
        st.subheader("Перерасход энергии")
        if "excess_consumption" in kpis:
            excess_data = kpis["excess_consumption"]
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Перерасход (кВт·ч)", f"{excess_data.get('excess_kwh', 0):,.2f}")
            with col2:
                st.metric("Перерасход (%)", f"{excess_data.get('excess_percent', 0):.2f}%")
        
        # Экономический эффект
        st.subheader("Экономический эффект")
        if "economic_effect" in kpis:
            economic_data = kpis["economic_effect"]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Экономия (кВт·ч)", f"{economic_data.get('savings_kwh', 0):,.2f}")
            with col2:
                st.metric("Экономия (руб)", f"{economic_data.get('savings_rub', 0):,.0f}")
            with col3:
                st.metric("Годовая экономия (кВт·ч)", f"{economic_data.get('annual_savings_kwh', 0):,.2f}")
            with col4:
                st.metric("Годовая экономия (руб)", f"{economic_data.get('annual_savings_rub', 0):,.0f}")

# Вкладка 4: Аномалии
with tab4:
    st.header("Обнаруженные аномалии")
    
    anomalies_data = get_anomalies(period_days)
    if anomalies_data and "anomalies" in anomalies_data:
        anomalies = anomalies_data["anomalies"]
        if anomalies:
            df_anomalies = pd.DataFrame(anomalies)
            st.dataframe(df_anomalies)
            
            # График аномалий
            if "timestamp" in df_anomalies.columns and "power_kwh" in df_anomalies.columns:
                fig = px.scatter(
                    df_anomalies,
                    x="timestamp",
                    y="power_kwh",
                    color="cause",
                    title="Аномалии энергопотребления",
                    labels={"power_kwh": "Энергопотребление (кВт·ч)", "timestamp": "Дата"}
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Аномалии не обнаружены")
    else:
        st.warning("Данные аномалий недоступны")

