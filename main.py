# main.py
# -*- coding: utf-8 -*-

import time
import traceback
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.exceptions import ApiError

from config import TOKEN, GROUP_ID


# ---------- Инициализация ----------

def create_vk_session():
    """Создаёт сессию VK и объект LongPoll."""
    session = vk_api.VkApi(token=TOKEN)
    longpoll = VkLongPoll(session, group_id=GROUP_ID)
    vk = session.get_api()
    return vk, longpoll


# ---------- Отправка сообщений ----------

def send_message(vk, user_id, text, keyboard=None, attachment=None):
    """Отправляет сообщение пользователю."""
    try:
        params = {
            "user_id": user_id,
            "message": text,
            "random_id": 0,
        }
        if keyboard is not None:
            params["keyboard"] = keyboard
        if attachment is not None:
            params["attachment"] = attachment
        vk.messages.send(**params)
    except ApiError as e:
        print(f"[API ERROR] Не удалось отправить сообщение {user_id}: {e}")
    except Exception as e:
        print(f"[ERROR] send_message: {e}")


# ---------- Обработчик команд ----------

def handle_command(vk, user_id, text):
    """
    Здесь вся логика бота.
    Добавляй свои команды в этот блок.
    """
    text = text.strip().lower()

    if text in ("начать", "start", "/start", "привет", "hi", "hello"):
        send_message(vk, user_id, "Привет! Я бот-менеджер бананов 🍌\nНапиши «помощь», чтобы увидеть команды.")
        return

    if text in ("помощь", "help", "/help"):
        send_message(
            vk, user_id,
            "Доступные команды:\n"
            "/start — приветствие\n"
            "/help — список команд\n"
            "/ping — проверка связи\n"
        )
        return

    if text in ("/ping", "ping"):
        send_message(vk, user_id, "pong 🏓")
        return

    # Заглушка для остальных сообщений — удали или замени на свою логику
    send_message(vk, user_id, "Я тебя не понял. Напиши «помощь».")


# ---------- Главный цикл ----------

def main():
    print("Запуск бота...")

    while True:
        try:
            vk, longpoll = create_vk_session()
            print(f"Бот запущен. Группа ID: {GROUP_ID}")

            for event in longpoll.listen():
                if event.type != VkEventType.MESSAGE_NEW:
                    continue
                if not event.to_me:
                    continue

                user_id = event.user_id
                text = event.text or ""

                print(f"[MSG] от {user_id}: {text}")

                try:
                    handle_command(vk, user_id, text)
                except Exception as e:
                    print(f"[HANDLER ERROR] {e}")
                    traceback.print_exc()

        except KeyboardInterrupt:
            print("Остановка бота по Ctrl+C.")
            break

        except Exception as e:
            print(f"[LONGPOLL ERROR] {e}")
            traceback.print_exc()
            print("Переподключение через 5 секунд...")
            time.sleep(5)


if __name__ == "__main__":
    main()
