from fastapi import FastAPI, HTTPException
from telethon import TelegramClient
import os
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


app = FastAPI()

API_ID = '858408'
API_HASH = 'c42722e7a3d3896caf40e74a1c4ecba9'
SESSION_DIR = os.path.join(os.getcwd(), 'sessions')
os.makedirs(SESSION_DIR, exist_ok=True)

# Временное хранилище phone_code_hash для каждого номера
phone_hash_store = {}

@app.post("/send-code/")
async def send_code(phone: str):
    print(phone)
    logger.info(f"Получен запрос на отправку кода для телефона: {phone}")
    session_name = os.path.join(SESSION_DIR, "session_" + phone.replace("+", ""))
    

    client = TelegramClient(session_name, API_ID, API_HASH)

    try:
        await client.connect()
        logger.info("Клиент Telegram подключён")
        if not await client.is_user_authorized():
            # Отправляем код и сохраняем phone_code_hash
            result = await client.send_code_request(phone)
            phone_hash_store[phone] = result.phone_code_hash
            logger.info(f"Код успешно отправлен, phone_code_hash сохранён для телефона: {phone}")
            return {"message": f"Код отправлен на номер {phone}", "success": True}
        logger.info("Пользователь уже авторизован")
        return {"message": "Пользователь уже авторизован", "success": True}
    except Exception as e:
        logger.error(f"Ошибка при отправке кода: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.disconnect()
        logger.info("Клиент Telegram отключён")


@app.post("/verify-code/")
async def verify_code(phone: str, code: str):
    logger.info(f"Получен запрос на подтверждение кода для телефона: {phone}")
    session_name = os.path.join(SESSION_DIR, "session_" + phone.replace("+", ""))
    client = TelegramClient(session_name, API_ID, API_HASH)

    try:
        # Проверяем наличие phone_code_hash для телефона
        phone_code_hash = phone_hash_store.get(phone)
        if not phone_code_hash:
            raise HTTPException(status_code=400, detail="Код не был отправлен или истёк")

        await client.connect()
        logger.info("Клиент Telegram подключён")

        # Завершаем авторизацию
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        logger.info(f"Код подтверждён для телефона: {phone}")

        # Удаляем сохранённый hash после успешной авторизации
        del phone_hash_store[phone]

        return {"message": f"Авторизация завершена для номера {phone}", "success": True}
    except Exception as e:
        logger.error(f"Ошибка при подтверждении кода: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.disconnect()
        logger.info("Клиент Telegram отключён")
