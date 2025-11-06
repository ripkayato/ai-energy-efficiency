import streamlit as st
import requests
import os

st.set_page_config(page_title="Прогноз НПЗ")
st.title("Прогноз энергопотребления НПЗ")

try:
    # Используем имя сервиса в Docker или localhost для локальной разработки
    api_url = os.getenv("API_URL", "http://localhost:8000/forecast")
    data = requests.get(api_url).json()
    if "error" not in data:
        st.line_chart([d['yhat'] for d in data])
    else:
        st.warning(data["error"])
except Exception as e:
    st.error(f"API недоступен: {e}")

