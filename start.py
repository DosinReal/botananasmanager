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