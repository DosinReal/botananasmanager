import random
import datetime
from config import (
    ROB_PROTECTION_LEVEL, ROB_PERCENT, ROB_COOLDOWN_HOURS, ARREST_HOURS,
    to_currency, to_rub, currency_symbol
)
from db import get_user, update_user, add_balance, cursor, conn


def cmd_rob(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import parse_user_id, mention, is_arrested

    if is_arrested(user_id):
        send(peer_id, "🚔 Ты в тюрьме, грабить нельзя.")
        return

    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return

    if u['rob_cooldown']:
        cd = datetime.datetime.fromisoformat(u['rob_cooldown'])
        if datetime.datetime.now() < cd:
            left = (cd - datetime.datetime.now()).total_seconds()
            send(peer_id, f"⏳ Кд грабежа: {int(left//60)}мин {int(left%60)}с.")
            return

    if not args:
        send(peer_id, "📌 ограбить [id]")
        return

    target = parse_user_id(args[0], vk)
    if not target or target == user_id:
        send(peer_id, "❌ Неверный ID.")
        return

    tu = get_user(target)
    if not tu['registered']:
        send(peer_id, "❌ Игрок не зарегистрирован.")
        return

    if tu['level'] < ROB_PROTECTION_LEVEL:
        send(peer_id, f"🛡 Игрок защищён до {ROB_PROTECTION_LEVEL} ур. (у него {tu['level']}).")
        return

    if is_arrested(target):
        send(peer_id, "🚔 Жертва в тюрьме.")
        return

    victim_bal = tu.get(f'balance_{tu["country"]}') or 0
    if victim_bal < 100:
        send(peer_id, "❌ У жертвы слишком мало денег на руках.")
        return

    cd_until = datetime.datetime.now() + datetime.timedelta(hours=ROB_COOLDOWN_HOURS)
    update_user(user_id, rob_cooldown=cd_until.isoformat())

    if random.random() < 0.5:
        stolen = victim_bal * ROB_PERCENT // 100
        update_user(target, **{f'balance_{tu["country"]}': victim_bal - stolen})
        stolen_rub = to_rub(stolen, tu['country'])
        stolen_my = to_currency(stolen_rub, u['country'])
        add_balance(user_id, stolen_my, currency=u['country'], note=f'rob {target}', tx_type='rob')
        sym = currency_symbol(u['country'])
        vsym = currency_symbol(tu['country'])
        send(peer_id, f"🥷 Успех! Ты ограбил {mention(target, vk)}\n💰 +{stolen_my:,} {sym}".replace(',', ' '))
        try:
            send(target, f"🥷 Тебя ограбили! -{stolen:,} {vsym}".replace(',', ' '))
        except Exception:
            pass
    else:
        arrest_until = datetime.datetime.now() + datetime.timedelta(hours=ARREST_HOURS)
        update_user(user_id, arrest_until=arrest_until.isoformat())
        send(peer_id, f"🚔 Провал! Поймали. Арест {ARREST_HOURS}ч.")


def cmd_arrest_info(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import parse_user_id, mention
    target = user_id
    if args:
        target = parse_user_id(args[0], vk) or user_id
    tu = get_user(target)
    if not tu.get('arrest_until'):
        send(peer_id, f"✅ {mention(target, vk)} не в тюрьме.")
        return
    until = datetime.datetime.fromisoformat(tu['arrest_until'])
    if datetime.datetime.now() >= until:
        update_user(target, arrest_until=None)
        send(peer_id, f"✅ {mention(target, vk)} вышел.")
        return
    left = (until - datetime.datetime.now()).total_seconds()
    send(peer_id, f"🚔 {mention(target, vk)} в тюрьме: {int(left//3600)}ч {int((left%3600)//60)}мин")


def cmd_police_fine(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import parse_user_id, mention
    u = get_user(user_id)
    if u['job'] != 'police':
        send(peer_id, "❌ Только полиция.")
        return
    if len(args) < 2:
        send(peer_id, "📌 штраф [id] [сумма]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    tu = get_user(target)
    if not tu.get('arrest_until'):
        send(peer_id, "❌ Не в тюрьме.")
        return
    until = datetime.datetime.fromisoformat(tu['arrest_until'])
    if datetime.datetime.now() >= until:
        send(peer_id, "❌ Уже вышел.")
        return
    try:
        amount = int(args[1])
    except ValueError:
        send(peer_id, "❌ Числом.")
        return
    if amount <= 0:
        send(peer_id, "❌ > 0")
        return
    victim_bal = tu.get(f'balance_{tu["country"]}') or 0
    if victim_bal < amount:
        send(peer_id, "❌ Мало у задержанного.")
        return
    update_user(target, **{f'balance_{tu["country"]}': victim_bal - amount})
    amount_rub = to_rub(amount, tu['country'])
    cursor.execute('UPDATE countries SET treasury = treasury + ? WHERE code = ?',
                   (amount_rub, u['country']))
    conn.commit()
    send(peer_id, f"👮 Штраф {mention(target, vk)}: {amount:,} → казна".replace(',', ' '))
    try:
        send(target, f"👮 Штраф: {amount:,}".replace(',', ' '))
    except Exception:
        pass