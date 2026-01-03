from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from pathlib import Path
from typing import Dict

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBasic()

USERS_FILE = Path(__file__).parent.parent / "users.txt"

def load_users() -> Dict[str, dict]:
    """Загружает пользователей из файла"""
    users = {}
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split(':')
                    if len(parts) >= 2:
                        username = parts[0]
                        password = parts[1]
                        fio = parts[2] if len(parts) >= 3 else username  # ✅ ВОТ ЭТОЙ СТРОКИ НЕ ХВАТАЛО

                        users[username] = {
                            "password": password,
                            "fio": fio,
                        }
    return users

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Проверяет учётные данные и возвращает username"""
    users = load_users()
    
    if credentials.username not in users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учётные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    user = users[credentials.username]
    stored_password = user["password"]
    
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        stored_password.encode("utf8")
    )
    
    if not is_correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учётные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return {
    "username": credentials.username,
    "fio": user["fio"],
    }


@router.get("/me")
async def get_current_user(username: str = Depends(verify_credentials)):
    """Получить информацию о текущем пользователе"""
    return {
        "username": username,
        "authenticated": True
    }

@router.post("/logout")
async def logout():
    """Выход из системы"""
    return {"message": "Logout successful"}
