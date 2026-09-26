import re
import datetime
import logging
from db import get_user, update_user

logger = logging.getLogger(__name__)

def has_rank(user_id, min_rank):
    return get_user(user_id)['rank'] >= min_rank

def is_real_creator(user_id):
    """Настоящий создатель — из списка CREATOR_IDS в конфиге."""
    from config import CREATOR_IDS
    return user_id in CREATOR_IDS

def is_owner(user_id):
    """Владелец/создатель — из конфига, из таблицы owners ИЛИ глобальная роль 100."""
    from db import is_owner_db, get_global_role
    if is_owner_db(user_id):
        return True
    return get_global_role(user_id) == 100

def is_tech_admin(user_id):
    """Тех. админ — глобальная роль 90+ ИЛИ владелец/создатель."""
    from db import get_global_role
    if is_owner(user_id):
        return True
    return get_global_role(user_id) >= 90

def is_global_helper(user_id):
    """Глобальный Хелпер (80+) — включая тех.админа и владельца."""
    from db import get_global_role
    return get_global_role(user_id) >= 80

def parse_user_id(text, vk=None):
    if not text:
        return None
    user_id = None
    m = re.search(r'\[id(\d+)\|', text)
    if m:
        user_id = int(m.group(1))
    if user_id is None:
        m = re.search(r'@id(\d+)', text)
        if m:
            user_id = int(m.group(1))
    if user_id is None and text.isdigit():
        user_id = int(text)
    if user_id is None:
        m = re.search(r'@([a-zA-Z0-9_\.]+)', text)
        if m and vk:
            try:
                info = vk.users.get(user_ids=m.group(1))
                if info:
                    user_id = info[0]['id']
            except Exception:
                pass
    if user_id is not None:
        get_user(user_id)
    return user_id

def get_user_name(user_id, vk=None):
    u = get_user(user_id)
    if u.get('nickname'):
        return u['nickname']
    if vk:
        try:
            info = vk.users.get(user_ids=user_id)
            if info:
                first = info[0].get('first_name', '') or ''
                last = info[0].get('last_name', '') or ''
                name = f"{first} {last}".strip()
                if name:
                    return name
        except Exception:
            pass
    return f"id{user_id}"

def mention(user_id, vk=None):
    name = get_user_name(user_id, vk)
    return f"[id{user_id}|{name}]"

def extract_chat_id(peer_id):
    if peer_id > 2_000_000_000:
        return peer_id - 2_000_000_000
    return None

def is_muted(user_id):
    u = get_user(user_id)
    if u.get('mute_until'):
        try:
            until = datetime.datetime.fromisoformat(u['mute_until'])
            if datetime.datetime.now() < until:
                return True
            update_user(user_id, mute_until=None)
        except Exception:
            pass
    return False

def is_arrested(user_id):
    u = get_user(user_id)
    if u.get('arrest_until'):
        try:
            until = datetime.datetime.fromisoformat(u['arrest_until'])
            if datetime.datetime.now() < until:
                return True
            update_user(user_id, arrest_until=None)
        except Exception:
            pass
    return False

def check_ban(user_id):
    from db import cursor
    cursor.execute('SELECT 1 FROM bans WHERE user_id = ?', (user_id,))
    if cursor.fetchone():
        return True
    cursor.execute('SELECT 1 FROM global_bans WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None

def is_global_banned(user_id):
    from db import cursor
    cursor.execute('SELECT 1 FROM global_bans WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None

def add_message_stat(user_id):
    from config import XP_PER_MESSAGE
    from db import add_xp
    u = get_user(user_id)
    update_user(user_id, messages_total=(u.get('messages_total') or 0) + 1)
    add_xp(user_id, XP_PER_MESSAGE)

def send_message(vk, peer_id, text, retries=3):
    from vk_api.utils import get_random_id
    import time as _time
    for attempt in


range(retries):
        try:
            vk.messages.send(peer_id=peer_id, message=text, random_id=get_random_id())
            return True
        except Exception as e:
            logger.warning(f"send_message попытка {attempt+1}/{retries}: {e}")
            if attempt < retries - 1:
                _time.sleep(1)
    logger.error(f"send_message не смог отправить → {peer_id}")
    return False

def delete_message(vk, peer_id, msg_id):
    try:
        vk.messages.delete(message_ids=[msg_id], peer_id=peer_id, delete_for_all=True)
        return True
    except Exception as e:
        logger.warning(f"delete_message error: {e}")
        return False

def kick_user_from_chat(vk, chat_id, user_id):
    try:
        vk.messages.removeChatUser(chat_id=chat_id, user_id=user_id)
        return True
    except Exception as e:
        logger.error(f"kick error {user_id} from {chat_id}: {e}")
        return False


start.py


import random
from config import COUNTRIES, CITIES, START_BALANCE_RUB, to_currency, currency_symbol
from db import get_user, update_user, add_balance

def cmd_start(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if u['registered']:
        send(peer_id, f"✅ Ты уже зарегистрирован!\n🏳️ {u['country']} | 🏙 {u['city']}")
        return

    if not args:
        lines = ["🌍 Выбери страну: !старт [код]\n"]
        for code, name, curr, rate, emoji in COUNTRIES:
            lines.append(f"{emoji} {code} — {name} ({curr})")
        send(peer_id, "\n".join(lines))
        return

    code = args[0].upper()
    valid = {c[0] for c in COUNTRIES}
    if code not in valid:
        send(peer_id, f"❌ Неверный код. Доступно: {', '.join(valid)}")
        return

    start_amount = to_currency(START_BALANCE_RUB, code)
    city = random.choice(CITIES[code])
    update_user(user_id, country=code, city=city, registered=1)
    add_balance(user_id, start_amount, currency=code, note='старт', tx_type='start')

    sym = currency_symbol(code)
    send(peer_id, f"🎉 Добро пожаловать!\n🏳️ {code} | 🏙 {city}\n💰 {start_amount:,} {sym}".replace(',', ' '))
