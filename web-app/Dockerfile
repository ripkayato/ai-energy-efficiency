FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py streamlit_app.py .
CMD ["python", "app.py"]