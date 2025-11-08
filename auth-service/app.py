from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
import time
import os

# Конфигурация
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# FastAPI приложение
app = FastAPI(title="Auth Service", description="Сервис авторизации для энергетической системы")

# Безопасность
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Подключение к БД
max_retries = 10
retry_delay = 2
engine = None

for attempt in range(max_retries):
    try:
        engine = create_engine('postgresql://user:pass@database:5432/energy')
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Подключение к БД установлено")
        break
    except Exception as e:
        if attempt < max_retries - 1:
            print(f"Попытка подключения {attempt + 1}/{max_retries} не удалась: {e}. Повтор через {retry_delay}с...")
            time.sleep(retry_delay)
        else:
            print(f"Ошибка подключения к БД после {max_retries} попыток: {e}")

# Модели
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    email: str = None

class UserInDB(User):
    hashed_password: str

# Утилиты
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_from_db(username: str):
    """Получить пользователя из БД"""
    if engine is None:
        return None
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT username, email, hashed_password FROM users WHERE username = :username"),
                {"username": username}
            )
            row = result.fetchone()
            if row:
                return UserInDB(
                    username=row[0],
                    email=row[1],
                    hashed_password=row[2]
                )
    except Exception as e:
        print(f"Ошибка получения пользователя: {e}")
    return None

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_from_db(username=username)
    if user is None:
        raise credentials_exception
    return user

# Эндпоинты
@app.get("/")
def read_root():
    return {"message": "Auth Service is running"}

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_from_db(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/register")
async def register(username: str, email: str, password: str):
    """Регистрация нового пользователя"""
    if engine is None:
        raise HTTPException(status_code=500, detail="Database connection not available")
    
    # Проверяем, существует ли пользователь
    existing_user = get_user_from_db(username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Хешируем пароль
    hashed_password = get_password_hash(password)
    
    # Сохраняем в БД
    try:
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO users (username, email, hashed_password) VALUES (:username, :email, :hashed_password)"),
                {
                    "username": username,
                    "email": email,
                    "hashed_password": hashed_password
                }
            )
            conn.commit()
        return {"message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering user: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

