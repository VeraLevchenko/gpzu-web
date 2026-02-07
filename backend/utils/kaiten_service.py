import aiohttp
import logging
from typing import Optional, Dict, Any
from core.config import KAITEN_API_TOKEN, KAITEN_DOMAIN, KAITEN_BOARD_ID, KAITEN_COLUMN_ID, KAITEN_LANE_ID

logger = logging.getLogger(__name__)
BASE_URL = f"https://{KAITEN_DOMAIN}/api/latest"

headers = {
    "Authorization": f"Bearer {KAITEN_API_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

async def create_card(
    title: str,
    description: str,
    due_date: Optional[str] = None,
    board_id: int = KAITEN_BOARD_ID,
    column_id: int = KAITEN_COLUMN_ID,
    lane_id: int = KAITEN_LANE_ID,
    type_id: Optional[int] = None,
    properties: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    if not board_id:
        logger.error("KAITEN_BOARD_ID не настроен")
        return None

    url = f"{BASE_URL}/cards"
    payload = {
        "board_id": board_id,
        "column_id": column_id,
        "lane_id": lane_id,
        "title": title,
        "description": description,
    }

    if type_id:
        payload["type_id"] = type_id
    if due_date:
        payload["due_date"] = due_date
    if properties:
        payload["properties"] = properties

    logger.info(f"Kaiten payload: {payload}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    card_id = data.get("id")
                    logger.info(f"Карточка создана: ID {card_id}")
                    return card_id
                else:
                    error_text = await resp.text()
                    logger.error(f"Ошибка Kaiten: {resp.status} - {error_text}")
                    return None
        except Exception as e:
            logger.exception(f"Ошибка: {e}")
            return None


async def add_card_member(card_id: int, user_id: int, member_type: int = 2) -> bool:
    """Добавить участника к карточке. type=2 — исполнитель."""
    url = f"{BASE_URL}/cards/{card_id}/members"
    payload = {"user_id": user_id, "type": member_type}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status in (200, 201):
                    logger.info(f"Исполнитель {user_id} добавлен к карточке {card_id}")
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"Ошибка добавления исполнителя: {resp.status} - {error_text}")
                    return False
        except Exception as e:
            logger.exception(f"Ошибка: {e}")
            return False
