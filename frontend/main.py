import requests
import telebot
from dotenv import load_dotenv
import os
import json
import hmac
import hashlib
import time
import asyncio
import io
import logging
from collections import defaultdict
from typing import List

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ContentType
from PIL import Image
import pytesseract


load_dotenv()
TOKEN = os.getenv("TOKEN")
BASE_URL = "http://0.0.0.0:8080"

bot  = telebot.TeleBot(TOKEN)


chat_indicator:bool = False

def generate_siganture(data:dict) -> str:
    KEY = os.getenv("SIGNATURE")
    data_to_ver = data.copy()
    data_to_ver.pop("signature",None)
    data_str = json.dumps(data_to_ver, sort_keys=True, separators=(',', ':'))
    expected_signature = hmac.new(KEY.encode(), data_str.encode(), hashlib.sha256).hexdigest()
    return str(expected_signature)

def start_api(username:str) -> bool:
    data = {
        "username":username
    }
    headers = {
        "X-Signature":generate_siganture(data),
        "X-Timestamp":str(int(time.time()))

    }
    resp = requests.post(f"{BASE_URL}/start",json = data,headers=headers)
    print(resp.status_code)
    print(resp.json())
    return resp.status_code == 200


bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище для медиагрупп (для обработки нескольких фото)
media_groups = defaultdict(list)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== КОМАНДЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    start_api(message.from_user.id)
    await message.answer(
        "👋 Привет! Я бот для распознавания текста с фото.\n\n"
        "📸 Отправь мне фотографию с текстом, и я попытаюсь его распознать.\n"
        "Можно отправлять несколько фото сразу (как альбом).\n\n"
        "📝 Поддерживаемые языки: русский, английский."
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await message.answer(
        "ℹ️ **Помощь по использованию бота:**\n\n"
        "1. 📸 Отправьте фото с текстом\n"
        "2. 📚 Можно отправить несколько фото сразу (выбрать из галереи)\n"
        "3. ⏳ Обработка занимает несколько секунд\n"
        "4. 🌍 Поддерживает русский и английский языки\n\n"
        "⚠️ Для лучшего распознавания:\n"
        "• Хорошее освещение\n"
        "• Четкий текст\n"
        "• Минимум искажений"
    )

# ==================== ОБРАБОТКА ФОТО ====================

async def preprocess_image(image_bytes: bytes) -> Image.Image:
    """Предобработка изображения для улучшения распознавания"""
    try:
        # Открываем изображение
        image = Image.open(io.BytesIO(image_bytes))
        
        # Конвертируем в RGB если нужно
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Увеличиваем контраст (можно раскомментировать если нужно)
        # from PIL import ImageEnhance
        # enhancer = ImageEnhance.Contrast(image)
        # image = enhancer.enhance(1.5)
        
        return image
    except Exception as e:
        logger.error(f"Ошибка предобработки: {e}")
        return Image.open(io.BytesIO(image_bytes))

async def extract_text_from_image(image_bytes: bytes) -> str:
    """Извлечение текста из изображения"""
    try:
        # Предобработка
        image = await preprocess_image(image_bytes)
        
        # Настройки для Tesseract
        custom_config = r'--oem 3 --psm 6'
        
        # Распознавание текста (русский + английский)
        text = pytesseract.image_to_string(
            image, 
            lang='rus+eng',
            config=custom_config
        )
        
        # Очистка текста
        text = text.strip()
        
        # Если текст слишком длинный, обрезаем
        if len(text) > 4000:
            text = text[:4000] + "..."
            
        return text if text else ""
        
    except Exception as e:
        logger.error(f"Ошибка OCR: {e}")
        return ""

@dp.message(F.photo)
async def handle_single_photo(message: Message):
    """Обработка одиночной фотографии"""
    try:
        # Отправляем статус обработки
        status_msg = await message.answer("🔍 Обрабатываю фото...")
        
        # Получаем фото максимального качества
        photo = message.photo[-1]
        
        # Скачиваем фото
        file = await bot.get_file(photo.file_id)
        photo_bytes = await bot.download_file(file.file_path)
        
        # Распознаем текст
        text = await extract_text_from_image(photo_bytes.read())
        
        # Удаляем статус
        await status_msg.delete()
        
        # Отправляем результат
        if text:
            # Если есть подпись к фото, добавляем ее
            caption = f"📝 **Текст с фото:**\n\n{text}"
            
            if message.caption:
                caption = f"📋 **Подпись:** {message.caption}\n\n" + caption
            
            await message.answer(caption)
        else:
            await message.answer("❌ Текст на фото не найден или не распознан.\n"
                                "Попробуйте фото с более четким текстом.")
            
    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}")
        await message.answer(f"⚠️ Ошибка при обработке фото: {str(e)}")

# ==================== ОБРАБОТКА НЕСКОЛЬКИХ ФОТО ====================

@dp.message(F.media_group_id)
async def handle_media_group_start(message: Message):
    """Начало обработки медиагруппы"""
    media_group_id = message.media_group_id
    
    # Если это первое фото в группе
    if media_group_id not in media_groups:
        # Добавляем в список
        media_groups[media_group_id] = {
            'messages': [],
            'user_id': message.from_user.id,
            'status_msg': None
        }
        
        # Отправляем статус
        status_msg = await message.answer(f"📚 Получено несколько фото. Обрабатываю...")
        media_groups[media_group_id]['status_msg'] = status_msg
        
    # Добавляем сообщение в группу
    media_groups[media_group_id]['messages'].append(message)
    
    # Ждем немного для сбора всех фото группы
    await asyncio.sleep(2)
    
    # Проверяем, все ли фото получены и обрабатываем
    await process_media_group_if_ready(media_group_id)

async def process_media_group_if_ready(media_group_id: str):
    """Обработка медиагруппы когда все фото получены"""
    if media_group_id not in media_groups:
        return
    
    group_data = media_groups[media_group_id]
    
    # Проверяем что есть фото для обработки
    photo_messages = [msg for msg in group_data['messages'] if msg.photo]
    
    if not photo_messages:
        return
    
    try:
        all_texts = []
        
        # Обрабатываем каждое фото
        for i, msg in enumerate(photo_messages, 1):
            # Получаем фото
            photo = msg.photo[-1]
            file = await bot.get_file(photo.file_id)
            photo_bytes = await bot.download_file(file.file_path)
            
            # Распознаем текст
            text = await extract_text_from_image(photo_bytes.read())
            
            if text:
                all_texts.append(f"📸 **Фото {i}:**\n{text}\n")
        
        # Удаляем статус сообщение
        if group_data['status_msg']:
            await group_data['status_msg'].delete()
        
        # Отправляем результат
        if all_texts:
            result_text = "\n".join(all_texts)
            
            # Разбиваем на части если слишком длинное
            if len(result_text) > 4000:
                parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
                for part in parts:
                    await bot.send_message(
                        chat_id=group_data['user_id'],
                        text=part
                    )
            else:
                await bot.send_message(
                    chat_id=group_data['user_id'],
                    text=f"📚 **Результаты ({len(all_texts)} фото):**\n\n{result_text}"
                )
        else:
            await bot.send_message(
                chat_id=group_data['user_id'],
                text="❌ Не удалось распознать текст ни на одной фотографии."
            )
    
    except Exception as e:
        logger.error(f"Ошибка обработки медиагруппы: {e}")
        await bot.send_message(
            chat_id=group_data['user_id'],
            text=f"⚠️ Ошибка при обработке фото: {str(e)}"
        )
    
    finally:
        # Очищаем группу
        if media_group_id in media_groups:
            del media_groups[media_group_id]

# ==================== ОБРАБОТКА ТЕКСТА ====================

@dp.message(F.text)
async def handle_text(message: Message):
    """Обработка текстовых сообщений"""
    text = message.text.strip()
    
    if text.lower() in ['привет', 'hello', 'hi']:
        await message.answer("👋 Привет! Отправь мне фото с текстом для распознавания.")
    elif text.lower() in ['спасибо', 'thanks', 'thank you']:
        await message.answer("😊 Рад был помочь!")
    else:
        await message.answer(
            "🤔 Я понимаю только команды и фотографии.\n"
            "Попробуй:\n"
            "/start - начать работу\n"
            "/help - помощь\n"
            "📸 или отправь фото с текстом"
        )

# ==================== ОБРАБОТКА ДРУГИХ ТИПОВ СООБЩЕНИЙ ====================

@dp.message(F.document)
async def handle_document(message: Message):
    """Обработка документов (например, файлы изображений)"""
    if message.document.mime_type and 'image' in message.document.mime_type:
        # Пробуем обработать как фото
        await message.answer("📄 Вижу, что это изображение. Пробую распознать текст...")
        
        # Скачиваем файл
        file = await bot.get_file(message.document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        
        # Распознаем текст
        text = await extract_text_from_image(file_bytes.read())
        
        if text:
            await message.answer(f"📝 **Текст из файла:**\n\n{text}")
        else:
            await message.answer("❌ Текст не найден.")
    else:
        await message.answer("📎 Я умею работать только с изображениями.")

@dp.message()
async def handle_other_messages(message: Message):
    """Обработка всех остальных типов сообщений"""
    await message.answer("❌ Я понимаю только текст и фотографии. Отправь фото с текстом для распознавания.")

# ==================== ЗАПУСК БОТА ====================

async def on_startup():
    """Действия при запуске бота"""
    logger.info("Бот запущен!")
    
    # Уведомляем админа
    try:
        await bot.send_message(ADMIN_ID, "🤖 Бот запущен и готов к работе!")
    except Exception as e:
        logger.error(f"Не удалось уведомить админа: {e}")

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Бот остановлен!")
    
    # Очищаем хранилище медиагрупп
    media_groups.clear()

async def main():
    """Основная функция запуска"""
    # Подключаем обработчики старта/остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запускаем бота
    asyncio.run(main())
