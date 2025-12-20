import requests
import telebot
from dotenv import load_dotenv
import os
from backend import start
import json
import hmac
import hashlib


load_dotenv()
TOKEN = os.getenv("TOKEN")
BASE_URL = "http://0.0.0.0:8080"

bot  = telebot.TeleBot(TOKEN)

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
        "X-Signature":generate_siganture(data)
    }
    resp = requests.post(f"{BASE_URL}/start",json = data,headers=headers)
    return resp.status_code == 200

@bot.message_handler(["start"])
def start_bot(message):
    user_id = message.from_user.id
    res = start_api(user_id)
    bot.send_message(message.chat.id,"Welcome")

@bot.message_handler(["chat"])
def start_chat(message):
    user_id = message.from_user.id


