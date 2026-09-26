from config import GANG_CREATE_PRICE_RUB, GANG_MAX_MEMBERS, GANG_ROLES, to_currency, currency_symbol
from db import get_user, update_user, add_balance, cursor, conn, now_iso

def cmd_gang(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import mention
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    if not u['gang_id']:
        send(peer_id, "🏴 Не в банде.\n!банда создать [имя] [тег]\n!банда вступить [id]\n!банда топ")
        return
    cursor.execute('SELECT * FROM gangs WHERE id = ?', (u['gang_id'],))
    g = cursor.fetchone()
    cursor.execute('SELECT COUNT(*) FROM users WHERE gang_id = ?', (g['id'],))
    members = cursor.fetchone()[0]
    send(peer_id,
         f"🏴 {g['name']} [{g['tag']}]\n"
         f"👑 {mention(g['leader_id'], vk)}\n"
         f"👥 {members}/{GANG_MAX_MEMBERS}\n"
         f"💰 {g['treasury']:,} ₽\n"
         f"🎖 {u['gang_role'] or '—'}".replace(',', ' '))

def cmd_gang_create(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    if u['gang_id']:
        send(peer_id, "❌ Уже в банде.")
        return
    if len(args) < 2:
        send(peer_id, "📌 банда создать [имя] [тег]")
        return
    name, tag = args[0][:20], args[1][:5].upper()
    cursor.execute('SELECT 1 FROM gangs WHERE name = ?', (name,))
    if cursor.fetchone():
        send(peer_id, "❌ Имя занято.")
        return
    price_local = to_currency(GANG_CREATE_PRICE_RUB, u['country'])
    sym = currency_symbol(u['country'])
    bal = u.get(f'balance_{u["country"]}') or 0
    if bal < price_local:
        send(peer_id, f"❌ Нужно {price_local:,} {sym}".replace(',', ' '))
        return
    update_user(user_id, **{f'balance_{u["country"]}': bal - price_local})
    cursor.execute('INSERT INTO gangs (name, tag, leader_id, created_at) VALUES (?, ?, ?, ?)',
                   (name, tag, user_id, now_iso()))
    gid = cursor.lastrowid
    conn.commit()
    update_user(user_id, gang_id=gid, gang_role='лидер')
    send(peer_id, f"🏴 Создана: {name} [{tag}]")

def cmd_gang_invite(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import parse_user_id, mention
    u = get_user(user_id)
    if not u['gang_id'] or u['gang_role'] not in ('лидер', 'зам'):
        send(peer_id, "❌ Только лидер/зам.")
        return
    if not args:
        send(peer_id, "📌 банда пригласить [id]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    tu = get_user(target)
    if not tu['registered'] or tu['gang_id']:
        send(peer_id, "❌ Не зарег или уже в банде.")
        return
    cursor.execute('SELECT COUNT(*) FROM users WHERE gang_id = ?', (u['gang_id'],))
    if cursor.fetchone()[0] >= GANG_MAX_MEMBERS:
        send(peer_id, "❌ Максимум.")
        return
    update_user(target, gang_id=u['gang_id'], gang_role='боец')
    send(peer_id, f"✅ {mention(target, vk)} принят.")
    try:
        send(target, "🏴 Ты принят в банду.")
    except Exception:
        pass

def cmd_gang_leave(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['gang_id']:
        send(peer_id, "❌ Не в банде.")
        return
    cursor.execute('SELECT * FROM gangs WHERE id = ?', (u['gang_id'],))
    g = cursor.fetchone()
    if g and g['leader_id'] == user_id:
        cursor.execute('UPDATE users SET gang_id = NULL, gang_role = NULL WHERE gang_id = ?', (u['gang_id'],))
        cursor.execute('DELETE FROM gangs WHERE id = ?', (u['gang_id'],))
        conn.commit()
        send(peer_id, "🏴 Банда распущена.")
        return
    update_user(user_id, gang_id=None, gang_role=None)
    send(peer_id, "🏴 Вышел из банды.")

def cmd_gang_kick(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import parse_user_id, mention
    u = get_user(user_id)
  if not u['gang_id'] or u['gang_role'] not in ('лидер', 'зам'):
        send(peer_id, "❌ Только лидер/зам.")
        return
    if not args:
        send(peer_id, "📌 банда кик [id]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    tu = get_user(target)
    if tu['gang_id'] != u['gang_id'] or tu['gang_role'] == 'лидер':
        send(peer_id, "❌ Нельзя.")
        return
    update_user(target, gang_id=None, gang_role=None)
    send(peer_id, f"✅ {mention(target, vk)} кикнут.")

def cmd_gang_promote(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import parse_user_id, mention
    u = get_user(user_id)
    if not u['gang_id'] or u['gang_role'] != 'лидер':
        send(peer_id, "❌ Только лидер.")
        return
    if len(args) < 2:
        send(peer_id, "📌 банда повысить [id] [зам/боец]")
        return
    target = parse_user_id(args[0], vk)
    role = args[1].lower()
    if role not in GANG_ROLES:
        send(peer_id, f"❌ Роль: {', '.join(GANG_ROLES)}")
        return
    tu = get_user(target)
    if tu['gang_id'] != u['gang_id']:
        send(peer_id, "❌ Не в твоей банде.")
        return
    update_user(target, gang_role=role)
    send(peer_id, f"✅ {mention(target, vk)} → {role}.")

def cmd_gang_deposit(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['gang_id']:
        send(peer_id, "❌ Не в банде.")
        return
    if not args:
        send(peer_id, "📌 банда вклад [сумма]")
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
    update_user(user_id, balance_RU=rub - amount)
    cursor.execute('UPDATE gangs SET treasury = treasury + ? WHERE id = ?', (amount, u['gang_id']))
    conn.commit()
    send(peer_id, f"💰 +{amount:,} ₽ в казну".replace(',', ' '))

def cmd_gang_top(user_id, peer_id, args, send, vk=None, msg_id=None):
    cursor.execute('''SELECT g.*, (SELECT COUNT(*) FROM users WHERE gang_id = g.id) AS members
        FROM gangs g ORDER BY g.treasury DESC LIMIT 10''')
    rows = cursor.fetchall()
    if not rows:
        send(peer_id, "🏴 Банд нет.")
        return
    medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    lines = ["🏆 Топ банд:\n"]
    for i, g in enumerate(rows):
        lines.append(f"{medals[i]} {g['name']} [{g['tag']}] — {g['members']} | {g['treasury']:,} ₽".replace(',', ' '))
    send(peer_id, "\n".join(lines))
