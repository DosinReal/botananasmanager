# config.py

import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = int(os.getenv("VK_GROUP_ID", "0"))

if not TOKEN:
    raise ValueError("Не задан VK_TOKEN в .env или переменных окружения")

if not GROUP_ID:
    raise ValueError("Не задан VK_GROUP_ID в .env или переменных окружения")
