from config import COUNTRIES, to_currency, currency_symbol
from db import get_user, update_user, cursor, conn, add_balance, log_action

def cmd_country(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import mention
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    cursor.execute('SELECT * FROM countries WHERE code = ?', (u['country'],))
    c = cursor.fetchone()
    cursor.execute('SELECT COUNT(*) FROM users WHERE country = ?', (u['country'],))
    pop = cursor.fetchone()[0]
    leader = mention(c['leader_id'], vk) if c['leader_id'] else '—'
    send(peer_id,
         f"{c['emoji']} {c['name']}\n"
         f"💱 {c['currency']} (1={c['rate']}₽)\n"
         f"👥 {pop}\n"
         f"💰 {c['treasury']:,} ₽\n"
         f"👑 {leader}".replace(',', ' '))

def cmd_treasury(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    cursor.execute('SELECT * FROM countries WHERE code = ?', (u['country'],))
    c = cursor.fetchone()
    send(peer_id, f"💰 {c['emoji']} {c['name']}: {c['treasury']:,} ₽".replace(',', ' '))

def cmd_treasury_give(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import parse_user_id, mention
    u = get_user(user_id)
    cursor.execute('SELECT * FROM countries WHERE code = ?', (u['country'],))
    c = cursor.fetchone()
    if not c or c['leader_id'] != user_id:
        send(peer_id, "❌ Только глава страны.")
        return
    if len(args) < 2:
        send(peer_id, "📌 казна выдать [id] [сумма]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    try:
        amount = int(args[1])
    except ValueError:
        send(peer_id, "❌ Числом.")
        return
    if amount <= 0 or amount > c['treasury']:
        send(peer_id, "❌ Неверная сумма.")
        return
    tu = get_user(target)
    if not tu['registered']:
        send(peer_id, "❌ Не зарег.")
        return
    target_amount = to_currency(amount, tu['country'])
    cursor.execute('UPDATE countries SET treasury = treasury - ? WHERE code = ?',
                   (amount, u['country']))
    conn.commit()
    add_balance(target, target_amount, currency=tu['country'], note='казна', tx_type='treasury')
    sym = currency_symbol(tu['country'])
    send(peer_id, f"✅ {amount:,} ₽ → {mention(target, vk)} ({target_amount:,} {sym})".replace(',', ' '))

def cmd_setleader(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import parse_user_id, mention, is_owner
    if not is_owner(user_id):
        send(peer_id, "❌ Только создатель.")
        return
    if len(args) < 2:
        send(peer_id, "📌 глава [id] [код]")
        return
    target = parse_user_id(args[0], vk)
    code = args[1].upper()
    valid = {c[0] for c in COUNTRIES}
    if not target or code not in valid:
        send(peer_id, "❌ Неверно.")
        return
    cursor.execute('UPDATE countries SET leader_id = ? WHERE code = ?', (target, code))
    conn.commit()
    log_action(user_id, f"Назначил главу {code}: {target}")
    send(peer_id, f"👑 {mention(target, vk)} — глава {code}.")

def cmd_unsetleader(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import is_owner
    if not is_owner(user_id):
        send(peer_id, "❌ Только создатель.")
        return
    if not args:
        send(peer_id, "📌 глава снять [код страны]")
        return
    code = args[0].upper()
    valid = {c[0] for c in COUNTRIES}
    if code not in valid:
        send(peer_id, f"❌ Неверный код. Доступно: {', '.join(valid)}")
        return
    cursor.execute('SELECT leader_id FROM countries WHERE code = ?', (code,))
    row = cursor.fetchone()
    if not row or not row['leader_id']:
        send(peer_id, f"❌ У страны {code} нет главы.")
        return
    cursor.execute('UPDATE countries SET leader_id = 0 WHERE code = ?', (code,))
    conn.commit()
    log_action(user_id, f"Снял главу с {code}
  ")
    send(peer_id, f"✅ Глава страны {code} снят.")

def cmd_top_countries(user_id, peer_id, args, send, vk=None, msg_id=None):
    cursor.execute('SELECT * FROM countries ORDER BY treasury DESC')
    rows = cursor.fetchall()
    medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣']
    lines = ["🏆 Топ стран:\n"]
    for i, c in enumerate(rows):
        lines.append(
            f"{medals[i]} {c['emoji']} {c['name']} — {c['treasury']:,} ₽".replace(',', ' ')
        )
    send(peer_id, "\n".join(lines))


config.py


TOKEN = "ВСТАВЬ СЮДА ТОКЕН"
CREATOR_IDS = [1030217520, 793215429]
BOT_GROUP_ID = ВСТАВЬ СЮДА ГРУРР ИД
DB_PATH = 'economy_bot.db'
LOG_PATH = 'economy_bot.log'

START_BALANCE_RUB = 1_000
DAILY_AMOUNT_RUB = 5_000
DAILY_COOLDOWN_HOURS = 24

TAX_PERCENT = 10
ROB_PROTECTION_LEVEL = 3
ARREST_HOURS = 3
ROB_PERCENT = 20
ROB_COOLDOWN_HOURS = 1

XP_PER_MESSAGE = 1
XP_PER_SHIFT = 10
XP_PER_LEVEL = 100

REPORT_HOUR = 21
REPORT_MINUTE = 0

COUNTRIES = [
    ('RU', 'Россия',   'Рубли',   1,   '🇷🇺'),
    ('US', 'США',      'Доллары', 100, '🇺🇸'),
    ('DE', 'Германия', 'Евро',    100, '🇩🇪'),
    ('JP', 'Япония',   'Иены',    1,   '🇯🇵'),
    ('CN', 'Китай',    'Юани',    10,  '🇨🇳'),
]
RATES = {code: rate for code, _, _, rate, _ in COUNTRIES}
CURRENCY_SYMBOLS = {'RU': '₽', 'US': '$', 'DE': '€', 'JP': '¥', 'CN': '元'}

CITIES = {
    'RU': ['Москва', 'Санкт-Петербург', 'Казань', 'Новосибирск'],
    'US': ['Нью-Йорк', 'Лос-Анджелес', 'Чикаго', 'Хьюстон'],
    'DE': ['Берлин', 'Мюнхен', 'Гамбург', 'Кёльн'],
    'JP': ['Токио', 'Осака', 'Киото', 'Нагоя'],
    'CN': ['Пекин', 'Шанхай', 'Гуанчжоу', 'Шэньчжэнь'],
}

JOBS = {
    'police': {'name': '👮 Полиция', 'salary_rub': 1_200, 'cooldown_minutes': 30, 'min_level': 1},
    'business': {'name': '💼 Бизнес', 'buy_price_rub': 100_000_000, 'hourly_income_rub': 800_000, 'min_level': 3},
    'taxi': {'name': '🚕 Такси', 'salary_rub': 2_000, 'cooldown_minutes': 20, 'min_level': 1},
}

HOUSES = {
    1: {'name': 'Квартира',  'price_rub': 20_000,     'hourly_income_rub': 100,      'safe_limit_rub': 10_000},
    2: {'name': 'Дом',       'price_rub': 150_000,    'hourly_income_rub': 800,      'safe_limit_rub': 100_000},
    3: {'name': 'Коттедж',   'price_rub': 800_000,    'hourly_income_rub': 5_000,    'safe_limit_rub': 500_000},
    4: {'name': 'Особняк',   'price_rub': 4_000_000,  'hourly_income_rub': 30_000,   'safe_limit_rub': 2_000_000},
    5: {'name': 'Пентхаус',  'price_rub': 20_000_000, 'hourly_income_rub': 200_000,  'safe_limit_rub': 10_000_000},
}

GANG_CREATE_PRICE_RUB = 15_000
GANG_MAX_MEMBERS = 30
GANG_ROLES = ['лидер', 'зам', 'боец']

SHOP_ITEMS = {
    'phone_1':  {'name': '📱 Кнопочный телефон',      'price_rub': 3_000,     'category': 'phone'},
    'phone_2':  {'name': '📱 Смартфон',               'price_rub': 25_000,    'category': 'phone'},
    'phone_3':  {'name': '📱 iPhone',                 'price_rub': 150_000,   'category': 'phone'},
    'acc_1':    {'name': '💎 Серебряная цепь',        'price_rub': 10_000,    'category': 'accessory'},
    'acc_2':    {'name': '💎 Золотая цепь',           'price_rub': 80_000,    'category': 'accessory'},
    'acc_3':    {'name': '💎 Бриллиантовый перстень', 'price_rub': 500_000,   'category': 'accessory'},
    'car_1':    {'name': '🚗 Лада',                   'price_rub': 50_000,    'category': 'car'},
    'car_2':    {'name': '🚗 BMW',                    'price_rub': 800_000,   'category': 'car'},
    'car_3':    {'name': '🚗 Lamborghini',            'price_rub': 5_000_000, 'category': 'car'},
}

RANK_NAMES = {
    100: 'Владелец',
    90: 'Тех. Администратор',
    78: 'Спец. Администратор', 70: 'Главный администратор',
    66: 'Куратор администрации', 58: 'След за Админами', 56: 'ГС ГОСС',
    55: 'ГС ОПГ', 53: 'ЗГС ГОСС', 52: 'ЗГС ОПГ', 50: 'Администратор',
    45: 'Мл. Администратор', 40: 'ГС Модераторов', 35: 'ЗГС Модераторов',
    30: 'След. Хелперов', 25: 'Ст.Модератор', 23: 'Пом. Ст. Модератора',
    20: 'Модератор', 15: 'Ст. Хелпер', 13: 'Пом Ст. Хелпера',
    10: 'Хелпер', 5: 'Мл. Хелпер', 0: 'Участник'
}

GLOBAL_ROLES = {
    100: '👑 Владелец бота',
    90:  '🛠 Тех. Администратор',
    80:  '🧰 Хелпер (глобальный)',
}

def to_currency(base_rub: int, currency_code: str) -> int:
    rate = RATES.get(currency_code, 1)
    return int(base_rub / rate)

def to_rub(amount: int, currency_code: str) -> int:
    rate = RATES.get(currency_code, 1)
    return int(amount * rate)

def currency_symbol(code: str) -> str:
    return CURRENCY_SYMB
  OLS.get(code, '₽')
