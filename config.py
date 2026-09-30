TOKEN = "ВСТАЫЬ СВОЙ ИД"
CREATOR_IDS = [840976146]
BOT_GROUP_ID = ВСТАВЬ ГРУПП ИД
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
    return CURRENCY_SYMBOLS.get(code, '₽')
