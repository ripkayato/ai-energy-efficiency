"""
Модуль аутентификации: проверка токенов, RBAC (ролевая модель доступа)
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
import time
import os
from typing import Optional


# Конфигурация
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Безопасность
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    email: Optional[str] = None
    role: Optional[str] = "user"


class UserInDB(User):
    hashed_password: str


class AuthModule:
    def __init__(self, db_url: str = "postgresql://user:pass@database:5432/energy"):
        self.db_url = db_url
        self.engine = None
        self._connect_db()

    def _connect_db(self, max_retries: int = 10, retry_delay: int = 2):
        """Подключение к БД с повторными попытками"""
        for attempt in range(max_retries):
            try:
                self.engine = create_engine(self.db_url)
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                print("Auth: Подключение к БД установлено")
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Auth: Попытка подключения {attempt + 1}/{max_retries} не удалась: {e}")
                    time.sleep(retry_delay)
                else:
                    print(f"Auth: Ошибка подключения к БД: {e}")
                    return False
        return False

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def get_user_from_db(self, username: str) -> Optional[UserInDB]:
        """Получить пользователя из БД"""
        if self.engine is None:
            return None
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT username, email, hashed_password, role FROM users WHERE username = :username"),
                    {"username": username}
                )
                row = result.fetchone()
                if row:
                    return UserInDB(
                        username=row[0],
                        email=row[1],
                        hashed_password=row[2],
                        role=row[3] if len(row) > 3 and row[3] else "user"
                    )
        except Exception as e:
            print(f"Auth: Ошибка получения пользователя: {e}")
        return None

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> User:
        """Получить текущего пользователя из токена"""
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
        
        user_db = self.get_user_from_db(username=username)
        if user_db is None:
            raise credentials_exception
        
        return User(username=user_db.username, email=user_db.email, role=user_db.role)

    async def require_role(self, required_role: str, current_user: User = Depends(get_current_user)):
        """Проверка роли пользователя (RBAC)"""
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role"
            )
        return current_user

    async def login(self, form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
        """Аутентификация пользователя"""
        user = self.get_user_from_db(form_data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not self.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": user.username, "role": user.role}, 
            expires_delta=access_token_expires
        )
        return Token(access_token=access_token, token_type="bearer")

    async def register(self, username: str, email: str, password: str, role: str = "user") -> dict:
        """Регистрация нового пользователя"""
        if self.engine is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        # Проверяем, существует ли пользователь
        existing_user = self.get_user_from_db(username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Хешируем пароль
        hashed_password = self.get_password_hash(password)
        
        # Сохраняем в БД
        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO users (username, email, hashed_password, role) 
                        VALUES (:username, :email, :hashed_password, :role)
                    """),
                    {
                        "username": username,
                        "email": email,
                        "hashed_password": hashed_password,
                        "role": role
                    }
                )
                conn.commit()
            return {"message": "User registered successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error registering user: {str(e)}")


# Глобальный экземпляр (будет инициализирован в app.py)
auth_module = None


def get_auth_module() -> AuthModule:
    """Получить экземпляр модуля аутентификации"""
    global auth_module
    if auth_module is None:
        auth_module = AuthModule()
    return auth_module


# Зависимости для использования в эндпоинтах
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Получить текущего пользователя"""
    return await get_auth_module().get_current_user(token)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Требовать роль admin"""
    return await get_auth_module().require_role("admin", current_user)

