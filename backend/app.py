from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "API работает!"}

@app.get("/forecast")
def forecast():
    return {"forecast": [1500, 1600, 1550, 1700]}