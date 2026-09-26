import datetime
from config import (
    DAILY_AMOUNT_RUB, DAILY_COOLDOWN_HOURS, TAX_PERCENT,
    COUNTRIES, HOUSES, JOBS, RATES, CURRENCY_SYMBOLS,
    to_currency, to_rub, currency_symbol
)
from db import (
    get_user, update_user, add_balance, get_balance,
    now_iso, cursor, conn, log_action
)

def cmd_profile(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import mention
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    job = JOBS.get(u['job'], {}).get('name', '—')
    house = HOUSES.get(u['house_level'], {}).get('name', '—')
    send(peer_id,
         f"👤 {mention(user_id, vk)}\n"
         f"🏳️ {u['country']} | 🏙 {u['city']}\n"
         f"📊 Ур. {u['level']}\n"
         f"💼 {job}\n🏠 {house}\n"
         f"📨 {u['messages_total']}")

def cmd_balance(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    lines = ["💰 Баланс:\n"]
    for code, name, curr, rate, emoji in COUNTRIES:
        sym = CURRENCY_SYMBOLS.get(code, '₽')
        bal = u.get(f'balance_{code}', 0) or 0
        lines.append(f"{emoji} {curr}: {bal:,} {sym}".replace(',', ' '))
    lines.append(f"\n🏦 Банк: {u['bank']:,} ₽".replace(',', ' '))
    lines.append(f"🔒 Сейф: {u['safe']:,} ₽".replace(',', ' '))
    send(peer_id, "\n".join(lines))

def cmd_daily(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    if u['last_daily']:
        last = datetime.datetime.fromisoformat(u['last_daily'])
        delta = (datetime.datetime.now() - last).total_seconds()
        if delta < DAILY_COOLDOWN_HOURS * 3600:
            left = DAILY_COOLDOWN_HOURS * 3600 - delta
            send(peer_id, f"⏳ Через {int(left//3600)}ч {int((left%3600)//60)}мин.")
            return
    amount = to_currency(DAILY_AMOUNT_RUB, u['country'])
    sym = currency_symbol(u['country'])
    add_balance(user_id, amount, currency=u['country'], note='daily', tx_type='daily')
    update_user(user_id, last_daily=now_iso())
    send(peer_id, f"🎁 +{amount:,} {sym}".replace(',', ' '))

def cmd_transfer(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import parse_user_id, mention
    if len(args) < 2:
        send(peer_id, "📌 перевод [id] [сумма]")
        return
    target = parse_user_id(args[0], vk)
    if not target or target == user_id:
        send(peer_id, "❌ Неверный ID.")
        return
    try:
        amount = int(args[1])
    except ValueError:
        send(peer_id, "❌ Сумма числом.")
        return
    if amount <= 0:
        send(peer_id, "❌ > 0")
        return
    u = get_user(user_id)
    tu = get_user(target)
    if not tu['registered']:
        send(peer_id, "❌ Не зарег.")
        return
    my_code = u['country']
    if get_balance(user_id, my_code) < amount:
        send(peer_id, "❌ Мало денег.")
        return
    their_code = tu['country']
    amount_rub = to_rub(amount, my_code)
    their_amount = to_currency(amount_rub, their_code)
    add_balance(user_id, -amount, currency=my_code, note=f'→{target}', tx_type='out')
    add_balance(target, their_amount, currency=their_code, note=f'←{user_id}', tx_type='in')
    send(peer_id, f"✅ {amount:,} → {mention(target, vk)} ({their_amount:,} их)".replace(',', ' '))
    try:
        send(target, f"💸 +{their_amount:,}".replace(',', ' '))
    except Exception:
        pass

def cmd_deposit(user_id, peer_id, args, send, vk=None, msg_id=None):
    if not args:
        send(peer_id, "📌 вклад [сумма]")
        return
    try:
        amount = int(args[0])
    except ValueError:
        send(peer_id, "❌ Числом.")
        return
    u = get_user(user_id)
    if amount <= 0 or (u.get('balance_RU') or 0) < amount:
        send(peer_id, "❌ Мало рублей.")
        return
    update_user(user_id, balance_RU=(u['balance_RU'] or 0) - amount, bank=u['bank'] + amount)
    send(peer_id, f"🏦 +{amount:,} ₽ в банк".replace(',', ' '))

def cmd_withdraw(user_id, peer_id, args, send, vk=None, msg_id=None):
    if not args:
        send(peer_id, "📌 снять [сумма]")
        return
    try:
        amount = int(args[0])
    except ValueError:
        send(peer_id, "❌ Числом.")
        return
    u = get_user(user_id)
    if amount <= 0 or u['bank'] < amount:
        send(peer_id, "❌ Мало в банке.")
        return
    update_user(user_id, balance_RU=(u['balance_RU'] or 0) + amount, bank=u['bank'] - amount)
    send(peer_id, f"💵 -{amount:,} ₽ из банка".replace(',', ' '))

def cmd_exchange(user_id, peer_id, args, send, vk=None, msg_id=None):
    if len(args) < 3:
        send(peer_id, "📌 обмен [сумма] [откуда] [куда]")
        return
    try:
        amount = int(args[0])
    except ValueError:
        send(peer_id, "❌ Числом.")
        return
    src, dst = args[1].upper(), args[2].upper()
    if src not in RATES or dst not in RATES or src == dst:
        send(peer_id, "❌ Неверные валюты (RU/US/DE/JP/CN).")
        return
    u = get_user(user_id)
    if amount <= 0 or (u.get(f'balance_{src}') or 0) < amount:
        send(peer_id, "❌ Мало.")
        return
    amount_rub = to_rub(amount, src)
    result = to_currency(amount_rub, dst)
    add_balance(user_id, -amount, currency=src, note=f'{src}→{dst}', tx_type='exch')
    add_balance(user_id, result, currency=dst, note=f'{src}→{dst}', tx_type='exch')
    send(peer_id, f"💱 {amount:,} {src} → {result:,} {dst}".replace(',', ' '))

def cmd_gived(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import parse_user_id, mention, is_owner
    if not is_owner(user_id):
        send(peer_id, "❌ Только владелец бота / создатель.")
        return
    if len(args) < 2:
        send(peer_id,
             "📌 gived [id] [сумма] [валюта]\n"
             "Валюта: RU / US / DE / JP / CN\n"
             "Пример: gived @user 5000\n"
             "Пример: gived @user 1000 US")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    try:
        amount = int(args[1])
    except ValueError:
        send(peer_id, "❌ Сумма должна быть числом.")
        return
    if amount <= 0:
        send(peer_id, "❌ Сумма должна быть больше 0.")
        return
    currency = args[2].upper() if len(args) >= 3 else None
    if currency is None:
        tu = get_user(target)
        if not tu.get('country'):
            send(peer_id, "❌ Игрок не зарегистрирован. Укажи валюту вручную (RU/US/DE/JP/CN).")
            return
        currency = tu['country']
    elif currency not in RATES:
        send(peer_id, "❌ Неверная валюта. Доступно: RU, US, DE, JP, CN")
        return
    add_balance(target, amount, currency=currency,
                note='выдача от создателя', tx_type='admin_give')
    log_action(user_id, f"Выдал {amount} {currency} игроку {target}")
    sym = currency_symbol(currency)
    send(peer_id,
         f"✅ Выдано {amount:,} {sym} → {mention(target, vk)}".replace(',', ' '))
    try:
        send(target, f"💰 Тебе выдано {amount:,} {sym}".replace(',', ' '))
    except Exception:
        pass

def apply_tax_and_pay(user_id, gross_rub, note='salary'):
    u = get_user(user_id)
    tax_rub = gross_rub * TAX_PERCENT // 100
    net_rub = gross_rub - tax_rub
    net = to_currency(net_rub, u['country'])
    add_balance(user_id, net, currency=u['country'], note=note, tx_type='salary')
    if u['country']:
        cursor.execute('UPDATE countries SET treasury = treasury + ? WHERE code = ?',
                       (tax_rub, u['country']))
        conn.commit()
    return net
  
