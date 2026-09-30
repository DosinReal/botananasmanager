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
    log_action(user_id, f"Снял главу с {code}")
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