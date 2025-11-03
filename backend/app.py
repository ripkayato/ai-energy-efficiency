from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "API работает!"}

@app.get("/forecast")
def forecast():
    return {"forecast": [1500, 1600, 1550, 1700]}

@app.get("/anomalies")
def anomalies():
    return {"anomalies": ["2025-01-01", "перерасход 200 кВт·ч"]}