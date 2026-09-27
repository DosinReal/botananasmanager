import datetime
from config import HOUSES, to_currency, currency_symbol
from db import get_user, update_user, now_iso


def cmd_houses(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    lines = ["🏠 Дома:\n"]
    for lvl, h in HOUSES.items():
        price = to_currency(h['price_rub'], u['country'])
        income = to_currency(h['hourly_income_rub'], u['country'])
        sym = currency_symbol(u['country'])
        lines.append(f"{lvl}. {h['name']} — {price:,} {sym} | +{income:,} {sym}/ч".replace(',', ' '))
    lines.append("\n📌 !дом купить [lvl]")
    send(peer_id, "\n".join(lines))


def cmd_house_buy(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    if not args or not args[0].isdigit():
        send(peer_id, "📌 дом купить [1-5]")
        return
    lvl = int(args[0])
    if lvl not in HOUSES:
        send(peer_id, "❌ 1-5")
        return
    h = HOUSES[lvl]
    if u['house_level'] >= lvl:
        send(peer_id, "❌ Уже есть не ниже.")
        return
    price_local = to_currency(h['price_rub'], u['country'])
    sym = currency_symbol(u['country'])
    bal = u.get(f'balance_{u["country"]}') or 0
    if bal < price_local:
        send(peer_id, f"❌ Нужно {price_local:,} {sym}".replace(',', ' '))
        return
    update_user(user_id, **{f'balance_{u["country"]}': bal - price_local},
                house_level=lvl, house_ts=now_iso())
    send(peer_id, f"🏠 Куплен: {h['name']}!")


def cmd_house_info(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered'] or not u['house_level']:
        send(peer_id, "❌ Нет дома. !дома")
        return
    h = HOUSES[u['house_level']]
    sym = currency_symbol(u['country'])
    inc = to_currency(h['hourly_income_rub'], u['country'])
    pending_h = 0
    if u['house_ts']:
        last = datetime.datetime.fromisoformat(u['house_ts'])
        pending_h = int((datetime.datetime.now() - last).total_seconds() // 3600)
    pending = to_currency(h['hourly_income_rub'] * pending_h, u['country'])
    send(peer_id,
         f"🏠 {h['name']}\n"
         f"📈 +{inc:,} {sym}/ч\n"
         f"⏳ Накоплено: {pending:,} {sym} ({pending_h}ч)\n"
         f"🔒 Сейф: {u['safe']:,} ₽\n"
         f"📌 !дом доход".replace(',', ' '))


def cmd_house_collect(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered'] or not u['house_level']:
        send(peer_id, "❌ Нет дома.")
        return
    if not u['house_ts']:
        update_user(user_id, house_ts=now_iso())
        send(peer_id, "✅ Таймер запущен.")
        return
    last = datetime.datetime.fromisoformat(u['house_ts'])
    hours = int((datetime.datetime.now() - last).total_seconds() // 3600)
    if hours < 1:
        send(peer_id, "⏳ <1ч.")
        return
    h = HOUSES[u['house_level']]
    total = h['hourly_income_rub'] * hours
    update_user(user_id, safe=u['safe'] + total, house_ts=now_iso())
    sym = currency_symbol(u['country'])
    total_local = to_currency(total, u['country'])
    send(peer_id, f"💰 +{total_local:,} {sym} в сейф".replace(',', ' '))


def cmd_safe_deposit(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered'] or not u['house_level']:
        send(peer_id, "❌ Сначала дом.")
        return
    if not args:
        send(peer_id, "📌 сейф положить [сумма]")
        return
    try:
        amount = int(args[0])
    except ValueError:
        send(peer_id, "❌ Числом.")
        return
    rub = u.get('balance_RU') or 0
    if amount <= 0 or rub < amount:
        send(peer_id, "❌ Мало.")
        return
    update_user(user_id, balance_RU=rub - amount, safe=u['safe'] + amount)
    send(peer_id, f"🔒 +{amount:,} ₽".replace(',', ' '))


def cmd_safe_withdraw(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered'] or not u['house_level']:
        send(peer_id, "❌ Сначала дом.")
        return
    if not args:
        send(peer_id, "📌 сейф снять [сумма]")
        return
    try:
        amount = int(args[0])
    except ValueError:
        send(peer_id, "❌ Числом.")
        return
    if amount <= 0 or u['safe'] < amount:
        send(peer_id, "❌ Мало.")
        return
    update_user(user_id, safe=u['safe'] - amount, balance_RU=(u.get('balance_RU') or 0) + amount)
    send(peer_id, f"💵 -{amount:,} ₽".replace(',', ' '))