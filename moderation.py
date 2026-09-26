import datetime
import time
from config import RANK_NAMES, GLOBAL_ROLES, CREATOR_IDS
from db import (
    get_user, update_user, cursor, conn, now_iso, log_action,
    get_global_role, set_global_role, remove_global_role, list_global_roles,
    add_owner, remove_owner, list_owners
)
from utils import (
    has_rank, parse_user_id, mention,
    extract_chat_id, delete_message, kick_user_from_chat,
    is_owner, is_tech_admin, is_real_creator
)

def cmd_mute(user_id, peer_id, args, send, vk=None, msg_id=None):
    if not (has_rank(user_id, 10) or is_owner(user_id)):
        send(peer_id, "❌ Недостаточно прав.")
        if msg_id:
            delete_message(vk, peer_id, msg_id)
        return
    if len(args) < 2:
        send(peer_id, "📌 mute [id] [минуты]")
        if msg_id:
            delete_message(vk, peer_id, msg_id)
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        if msg_id:
            delete_message(vk, peer_id, msg_id)
        return
    try:
        minutes = int(args[1])
    except ValueError:
        send(peer_id, "❌ Неверное время.")
        return
    if target == user_id:
        send(peer_id, "❌ Себя мутить нельзя.")
        return
    if is_real_creator(target) and not is_real_creator(user_id):
        send(peer_id, "❌ Нельзя тронуть настоящего создателя.")
        return
    if get_user(target)['rank'] >= get_user(user_id)['rank'] and not is_owner(user_id):
        send(peer_id, "❌ Нельзя мутить равного/высшего.")
        return
    if is_owner(target) and not is_owner(user_id):
        send(peer_id, "❌ Нельзя мутить владельца бота.")
        return
    until = (datetime.datetime.now() + datetime.timedelta(minutes=minutes)).isoformat()
    cursor.execute('INSERT OR REPLACE INTO mutes (user_id, until, reason, admin_id) VALUES (?, ?, ?, ?)',
                   (target, until, 'Мут', user_id))
    conn.commit()
    update_user(target, mute_until=until)
    log_action(user_id, f"Мут {target} на {minutes} мин.")
    send(peer_id, f"🔇 {mention(target, vk)} замучен на {minutes} мин.")
    try:
        send(target, f"🔇 Тебя замутили на {minutes} мин.")
    except Exception:
        pass
    if msg_id:
        delete_message(vk, peer_id, msg_id)

def cmd_unmute(user_id, peer_id, args, send, vk=None):
    if not (has_rank(user_id, 10) or is_owner(user_id)):
        send(peer_id, "❌ Недостаточно прав.")
        return
    if not args:
        send(peer_id, "📌 unmute [id]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    cursor.execute('DELETE FROM mutes WHERE user_id = ?', (target,))
    conn.commit()
    update_user(target, mute_until=None)
    log_action(user_id, f"Размут {target}")
    send(peer_id, f"🔊 С {mention(target, vk)} снят мут.")

def cmd_ban(user_id, peer_id, args, send, vk=None):
    if not (has_rank(user_id, 20) or is_owner(user_id)):
        send(peer_id, "❌ Недостаточно прав.")
        return
    if not args:
        send(peer_id, "📌 ban [id] [причина]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    if target == user_id:
        send(peer_id, "❌ Себя банить нельзя.")
        return
    if is_real_creator(target) and not is_real_creator(user_id):
        send(peer_id, "❌ Нельзя тронуть настоящего создателя.")
        return
    if get_user(target)['rank'] >= get_user(user_id)['rank'] and not is_owner(user_id):
        send(peer_id, "❌ Нельзя банить равного/высшего.")
        return
    if is_owner(target) and not is_owner(user_id):
        send(peer_id, "❌ Нельзя банить владельца бота.")
        return
    reason = ' '.join(args[1:]) if len(args) > 1 else 'Не указана'
    chat_id = extract_chat_id(peer_id)
    if chat_id:
        kick_user_from_chat(vk, chat_id, target)
    cursor.execute('INSERT OR REPLACE INTO bans (user_id, reason, timestamp, admin_id) VA


LUES (?, ?, ?, ?)',
                   (target, reason, now_iso(), user_id))
    conn.commit()
    log_action(user_id, f"Бан {target}: {reason}")
    send(peer_id, f"⛔ {mention(target, vk)} забанен.\n📄 Причина: {reason}")
    try:
        send(target, f"⛔ Ты забанен.\n📄 Причина: {reason}")
    except Exception:
        pass

def cmd_unban(user_id, peer_id, args, send, vk=None):
    if not (has_rank(user_id, 20) or is_owner(user_id)):
        send(peer_id, "❌ Недостаточно прав.")
        return
    if not args:
        send(peer_id, "📌 unban [id]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    cursor.execute('DELETE FROM bans WHERE user_id = ?', (target,))
    conn.commit()
    log_action(user_id, f"Разбан {target}")
    send(peer_id, f"✅ С {mention(target, vk)} снят бан.")

def cmd_warn(user_id, peer_id, args, send, vk=None):
    if not (has_rank(user_id, 10) or is_owner(user_id)):
        send(peer_id, "❌ Недостаточно прав.")
        return
    if len(args) < 2:
        send(peer_id, "📌 warn [id] [причина]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    reason = ' '.join(args[1:])
    cursor.execute('INSERT INTO warns (user_id, reason, moderator_id, timestamp) VALUES (?, ?, ?, ?)',
                   (target, reason, user_id, now_iso()))
    conn.commit()
    cursor.execute('SELECT COUNT(*) FROM warns WHERE user_id = ?', (target,))
    count = cursor.fetchone()[0]
    log_action(user_id, f"Варн {target}: {reason}")
    send(peer_id,
         f"⚠️ {mention(target, vk)} получил предупреждение.\n"
         f"📄 {reason}\n📊 Всего: {count}")
    try:
        send(target, f"⚠️ Ты получил предупреждение: {reason}\nВсего: {count}")
    except Exception:
        pass

def cmd_warns(user_id, peer_id, args, send, vk=None):
    if not (has_rank(user_id, 10) or is_owner(user_id)):
        send(peer_id, "❌ Недостаточно прав.")
        return
    target = user_id
    if args:
        target = parse_user_id(args[0], vk) or user_id
    cursor.execute('SELECT reason, moderator_id, timestamp FROM warns WHERE user_id = ? ORDER BY id DESC LIMIT 10',
                   (target,))
    rows = cursor.fetchall()
    if not rows:
        send(peer_id, f"📋 У {mention(target, vk)} нет предупреждений.")
        return
    lines = [f"📋 Предупреждения {mention(target, vk)}:\n"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['reason']}\n   👤 {mention(r['moderator_id'], vk)} | {r['timestamp'][:16]}")
    send(peer_id, "\n".join(lines))

def cmd_unwarn(user_id, peer_id, args, send, vk=None):
    if not (has_rank(user_id, 10) or is_owner(user_id)):
        send(peer_id, "❌ Недостаточно прав.")
        return
    if len(args) < 2:
        send(peer_id, "📌 унварн [id] [номер варна]\nСписок: !warns [id]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    try:
        num = int(args[1])
    except ValueError:
        send(peer_id, "❌ Номер числом.")
        return
    cursor.execute('SELECT id FROM warns WHERE user_id = ? ORDER BY id DESC', (target,))
    rows = cursor.fetchall()
    if not rows:
        send(peer_id, f"❌ У {mention(target, vk)} нет варнов.")
        return
    if num < 1 or num > len(rows):
        send(peer_id, f"❌ Номер от 1 до {len(rows)}.")
        return
    warn_id = rows[num - 1]['id']
    cursor.execute('DELETE FROM warns WHERE id = ?', (warn_id,))
    conn.commit()
    log_action(user_id, f"Снял варн #{num} у {target}")
    cursor.execute('SELECT COUNT(*) FROM warns WHERE user_id = ?', (target,))
    left = cursor.fetchone()[0]
    send(peer_id, f"✅ С {mention(target, vk)} снят варн #{num}.\n📊 Осталось: {left}")

def cmd_clear_warns(user_id, peer_id, args, send, vk=None):
    if not (has_rank(user_id, 50) or is_owner(user_id)):
        send(peer_id, "❌ Недо


статочно прав (нужно 50+).")
        return
    if not args:
        send(peer_id, "📌 clear_warns [id]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    cursor.execute('DELETE FROM warns WHERE user_id = ?', (target,))
    conn.commit()
    log_action(user_id, f"Снял все преды у {target}")
    send(peer_id, f"✅ С {mention(target, vk)} сняты все преды.")

def cmd_setrole(user_id, peer_id, args, send, vk=None):
    if not is_owner(user_id):
        send(peer_id, "❌ Только создатель.")
        return
    if len(args) < 2:
        roles_list = "\n".join([f"{r} — {RANK_NAMES[r]}" for r in sorted(RANK_NAMES.keys(), reverse=True)])
        send(peer_id, f"📋 Роли:\n{roles_list}\n\nsetrole [id] [ранг]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    try:
        new_rank = int(args[1])
    except ValueError:
        send(peer_id, "❌ Ранг числом.")
        return
    if new_rank not in RANK_NAMES:
        send(peer_id, "❌ Неверный ранг.")
        return
    update_user(target, rank=new_rank)
    log_action(user_id, f"Ранг {new_rank} → {target}")
    send(peer_id, f"✅ {mention(target, vk)} → {RANK_NAMES[new_rank]}.")

def cmd_myrole(user_id, peer_id, args, send, vk=None):
    u = get_user(user_id)
    g = get_global_role(user_id)
    lines = [f"👤 Твой ранг: {RANK_NAMES.get(u['rank'], 'Участник')} ({u['rank']})"]
    if g:
        lines.append(f"🌐 Глобальная роль: {GLOBAL_ROLES.get(g, g)} ({g})")
    if is_real_creator(user_id):
        lines.append("👑 Ты — настоящий создатель бота")
    send(peer_id, "\n".join(lines))

def cmd_roles(user_id, peer_id, args, send, vk=None):
    if not (has_rank(user_id, 5) or is_owner(user_id)):
        send(peer_id, "❌ Недостаточно прав (нужно 5+).")
        return
    lines = ["📋 Список ролей:\n"]
    for r in sorted(RANK_NAMES.keys(), reverse=True):
        lines.append(f"• {r} — {RANK_NAMES[r]}")
    send(peer_id, "\n".join(lines))

def cmd_setnick(user_id, peer_id, args, send, vk=None):
    if not (has_rank(user_id, 5) or is_owner(user_id)):
        send(peer_id, "❌ Недостаточно прав (нужно 5+).")
        return
    if not args:
        send(peer_id, "📌 setnick [ник] — себе\n📌 setnick [id] [ник] — другому")
        return
    potential = parse_user_id(args[0], vk)
    if potential and len(args) >= 2:
        target = potential
        nick = ' '.join(args[1:])
        if not is_owner(user_id):
            if get_user(target)['rank'] >= get_user(user_id)['rank'] and target != user_id:
                send(peer_id, "❌ Нельзя менять ник равному/высшему.")
                return
    else:
        target = user_id
        nick = ' '.join(args)
    if len(nick) > 30:
        send(peer_id, "❌ Ник до 30 символов.")
        return
    update_user(target, nickname=nick)
    if target == user_id:
        send(peer_id, f"✅ Твой ник: {nick}")
    else:
        send(peer_id, f"✅ {mention(target, vk)} получил ник: {nick}")

def cmd_ticket(user_id, peer_id, args, send, vk=None):
    if not args:
        send(peer_id, "📌 ticket [текст]")
        return
    text = ' '.join(args)
    cursor.execute('INSERT INTO tickets (user_id, text, status, timestamp) VALUES (?, ?, "open", ?)',
                   (user_id, text, now_iso()))
    conn.commit()
    tid = cursor.lastrowid
    send(peer_id, f"✅ Тикет #{tid} создан.")
    cursor.execute('SELECT user_id FROM users WHERE rank >= 5')
    for r in cursor.fetchall():
        if r['user_id'] == user_id:
            continue
        try:
            send(r['user_id'], f"🎫 Новый тикет #{tid} от {mention(user_id, vk)}:\n{text}")
        except Exception:
            pass

def cmd_tickets(user_id, peer_id, args, send, vk=None):
    from utils import is_global_helper
    if not (is_global_helper(user_id) or has_rank(user_id, 80)):
        send(peer_id, "❌ Только глобальный Хелпер (80+) и выше.")
        retu


rn
    cursor.execute('SELECT * FROM tickets WHERE status = "open" ORDER BY id')
    rows = cursor.fetchall()
    if not rows:
        send(peer_id, "📋 Открытых тикетов нет.")
        return
    lines = ["📋 Открытые тикеты:\n"]
    for t in rows:
        lines.append(f"#{t['id']} от {mention(t['user_id'], vk)}: {t['text']}")
    send(peer_id, "\n".join(lines))

def cmd_answer(user_id, peer_id, args, send, vk=None):
    from utils import is_global_helper
    if not (is_global_helper(user_id) or has_rank(user_id, 80)):
        send(peer_id, "❌ Только глобальный Хелпер (80+) и выше.")
        return
    if len(args) < 2:
        send(peer_id, "📌 answer [id] [ответ]")
        return
    try:
        tid = int(args[0])
    except ValueError:
        send(peer_id, "❌ Неверный ID.")
        return
    answer = ' '.join(args[1:])
    cursor.execute('SELECT user_id FROM tickets WHERE id = ? AND status = "open"', (tid,))
    row = cursor.fetchone()
    if not row:
        send(peer_id, "❌ Тикет не найден.")
        return
    cursor.execute('UPDATE tickets SET status = "closed", answer = ?, answered_by = ? WHERE id = ?',
                   (answer, user_id, tid))
    conn.commit()
    send(peer_id, f"✅ Тикет #{tid} закрыт.")
    try:
        send(row['user_id'], f"📩 Ответ на тикет #{tid}:\n{answer}")
    except Exception:
        pass

def cmd_rules(user_id, peer_id, args, send, vk=None):
    cursor.execute('SELECT text FROM rules ORDER BY id')
    rows = cursor.fetchall()
    if not rows:
        send(peer_id, "📋 Правила не установлены.")
        return
    lines = ["📜 Правила:\n"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['text']}")
    send(peer_id, "\n".join(lines))

def cmd_setrule(user_id, peer_id, args, send, vk=None):
    if not (has_rank(user_id, 70) or is_owner(user_id)):
        send(peer_id, "❌ Недостаточно прав (нужно 70+).")
        return
    if not args:
        send(peer_id, "📌 setrule [текст]")
        return
    cursor.execute('INSERT INTO rules (text) VALUES (?)', (' '.join(args),))
    conn.commit()
    send(peer_id, "✅ Правило добавлено.")

def cmd_delrule(user_id, peer_id, args, send, vk=None):
    if not (has_rank(user_id, 70) or is_owner(user_id)):
        send(peer_id, "❌ Недостаточно прав (нужно 70+).")
        return
    if not args or not args[0].isdigit():
        send(peer_id, "📌 delrule [номер]")
        return
    num = int(args[0])
    cursor.execute('SELECT id FROM rules WHERE id = ?', (num,))
    if not cursor.fetchone():
        send(peer_id, f"❌ Правило #{num} не найдено.")
        return
    cursor.execute('DELETE FROM rules WHERE id = ?', (num,))
    conn.commit()
    send(peer_id, f"✅ Правило #{num} удалено.")

def cmd_welcome(user_id, peer_id, args, send, vk=None):
    if not (has_rank(user_id, 66) or is_owner(user_id)):
        send(peer_id, "❌ Недостаточно прав (нужно 66+).")
        return
    if not args:
        cursor.execute('DELETE FROM welcome_settings WHERE peer_id = ?', (peer_id,))
        conn.commit()
        send(peer_id, "✅ Приветствие удалено.")
        return
    cursor.execute('INSERT OR REPLACE INTO welcome_settings (peer_id, message) VALUES (?, ?)',
                   (peer_id, ' '.join(args)))
    conn.commit()
    send(peer_id, "✅ Приветствие установлено.")

def cmd_announce(user_id, peer_id, args, send, vk=None):
    if not is_owner(user_id):
        send(peer_id, "❌ Только создатель.")
        return
    if not args:
        send(peer_id, "📌 announce [текст]")
        return
    msg = ' '.join(args)
    cursor.execute('SELECT peer_id FROM chats')
    chats = cursor.fetchall()
    count = 0
    for c in chats:
        try:
            send(c['peer_id'], f"📢 {msg}")
            count += 1
            time.sleep(0.1)
        except Exception:
            pass
    send(peer_id, f"✅ Отправлено в {count} бесед.")

def cmd_logs(user_id, peer_id, args, send, vk=None):
    if not is_tech_admin(user_id):
        send(peer_id, "❌ Только Тех. Админ


(90) / Владелец бота (100).")
        return
    cursor.execute('SELECT user_id, action, timestamp FROM logs ORDER BY id DESC LIMIT 20')
    rows = cursor.fetchall()
    if not rows:
        send(peer_id, "📋 Логов нет.")
        return
    lines = ["📋 Последние логи:\n"]
    for r in rows:
        lines.append(f"• {mention(r['user_id'], vk)}: {r['action']}\n  {r['timestamp'][:16]}")
    send(peer_id, "\n".join(lines))

def cmd_globalban(user_id, peer_id, args, send, vk=None):
    if not is_owner(user_id):
        send(peer_id, "❌ Только создатель.")
        return
    if not args:
        send(peer_id, "📌 globalban [id] [причина]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    if is_real_creator(target):
        send(peer_id, "❌ Нельзя забанить настоящего создателя.")
        return
    reason = ' '.join(args[1:]) if len(args) > 1 else 'Не указана'
    cursor.execute('INSERT OR REPLACE INTO global_bans (user_id, reason, timestamp, admin_id) VALUES (?, ?, ?, ?)',
                   (target, reason, now_iso(), user_id))
    conn.commit()
    log_action(user_id, f"Глобалбан {target}: {reason}")
    cursor.execute('SELECT peer_id FROM chats')
    chats = cursor.fetchall()
    kicked = 0
    for c in chats:
        cid = extract_chat_id(c['peer_id'])
        if cid and kick_user_from_chat(vk, cid, target):
            kicked += 1
            time.sleep(0.1)
    send(peer_id,
         f"🌍 {mention(target, vk)} — глобальный бан.\n"
         f"📄 {reason}\n🚪 Исключён из {kicked} бесед.")
    try:
        send(target, f"🌍 Ты глобально забанен.\n📄 Причина: {reason}")
    except Exception:
        pass

def cmd_unglobalban(user_id, peer_id, args, send, vk=None):
    if not is_owner(user_id):
        send(peer_id, "❌ Только создатель.")
        return
    if not args:
        send(peer_id, "📌 unglobalban [id]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    cursor.execute('DELETE FROM global_bans WHERE user_id = ?', (target,))
    conn.commit()
    log_action(user_id, f"Разглобалбан {target}")
    send(peer_id, f"✅ С {mention(target, vk)} снят глобальный бан.")

def cmd_chatlist(user_id, peer_id, args, send, vk=None):
    if not is_owner(user_id):
        send(peer_id, "❌ Только создатель.")
        return
    cursor.execute('SELECT peer_id FROM chats')
    rows = cursor.fetchall()
    if not rows:
        send(peer_id, "📋 Нет бесед.")
        return
    lines = ["📋 Беседы:\n"]
    for r in rows:
        cid = r['peer_id'] - 2_000_000_000 if r['peer_id'] > 2_000_000_000 else r['peer_id']
        lines.append(f"• peer_id: {r['peer_id']} (chat_id: {cid})")
    send(peer_id, "\n".join(lines))
  # ============================================================
#  ГЛОБАЛЬНЫЕ РОЛИ
# ============================================================

def cmd_addglobal(user_id, peer_id, args, send, vk=None):
    if not is_owner(user_id):
        send(peer_id, "❌ Только создатель.")
        return
    if len(args) < 2:
        roles = "\n".join([f"{lvl} — {name}" for lvl, name in sorted(GLOBAL_ROLES.items(), reverse=True)])
        send(peer_id, f"📋 Глобальные роли:\n{roles}\n\naddglobal [id] [уровень]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    try:
        level = int(args[1])
    except ValueError:
        send(peer_id, "❌ Уровень числом.")
        return
    if level not in GLOBAL_ROLES:
        send(peer_id, "❌ Неверная роль.")
        return
    if is_real_creator(target):
        send(peer_id, "❌ Настоящий создатель уже имеет все права.")
        return
    if level == 100 and not is_real_creator(user_id):
        send(peer_id, "❌ Только настоящий создатель может выдать роль 100.")
        return
    set_global_role(target, level, user_id)
    log_action(user_id, f"Выдал глобальную роль {level} ({GLOBAL_ROLES[level]}) → {target}")
    send(peer_id, f"✅ {mention(target, vk)} → {GLOBAL_ROLES[level]}.")

def cmd_delglobal(user_id, peer_id, args, send, vk=None):
    if not is_owner(user_id):
        send(peer_id, "❌ Только создатель.")
        return
    if not args:
        send(peer_id, "📌 delglobal [id]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    if is_real_creator(target):
        send(peer_id, "❌ Настоящего создателя нельзя снять.")
        return
    if get_global_role(target) == 0:
        send(peer_id, f"❌ У {mention(target, vk)} нет глобальной роли.")
        return
    remove_global_role(target)
    log_action(user_id, f"Снял глобальную роль у {target}")
    send(peer_id, f"✅ С {mention(target, vk)} снята глобальная роль.")

def cmd_gstaff(user_id, peer_id, args, send, vk=None):
    lines = ["🌐 ГЛОБАЛЬНЫЙ ПЕРСОНАЛ\n━━━━━━━━━━━━━━━━━━━━━"]
    lines.append("\n👑 Настоящие создатели:")
    for cid in CREATOR_IDS:
        lines.append(f"  {mention(cid, vk)}")
    rows = list_global_roles()
    if rows:
        by_role = {}
        for r in rows:
            by_role.setdefault(r['role_level'], []).append(r['user_id'])
        for lvl in sorted(by_role.keys(), reverse=True):
            name = GLOBAL_ROLES.get(lvl, f"Уровень {lvl}")
            lines.append(f"\n{name} ({lvl}):")
            for uid in by_role[lvl]:
                lines.append(f"  {mention(uid, vk)}")
    send(peer_id, "\n".join(lines))

# ============================================================
#  СОЗДАТЕЛИ (несколько)
# ============================================================

def cmd_addowner(user_id, peer_id, args, send, vk=None):
    if not is_real_creator(user_id):
        send(peer_id, "❌ Только настоящий создатель (из конфига).")
        return
    if not args:
        send(peer_id, "📌 addowner [id]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    if target == user_id:
        send(peer_id, "❌ Ты уже создатель.")
        return
    add_owner(target, user_id)
    log_action(user_id, f"Сделал создателем {target}")
    send(peer_id, f"👑 {mention(target, vk)} теперь создатель (равные права).")

def cmd_delowner(user_id, peer_id, args, send, vk=None):
    if not is_real_creator(user_id):
        send(peer_id, "❌ Только настоящий создатель (из конфига).")
        return
    if not args:
        send(peer_id, "📌 delowner [id]")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    if target == user_id:
        send(peer_id, "❌ Себя снять нельзя.")
        return
    if is_real_creator(target):


send(peer_id, "❌ Настоящего создателя снять нельзя.")
        return
    remove_owner(target)
    log_action(user_id, f"Снял создателя {target}")
    send(peer_id, f"✅ {mention(target, vk)} больше не создатель.")

def cmd_owners(user_id, peer_id, args, send, vk=None):
    lines = ["👑 СОЗДАТЕЛИ БОТА\n━━━━━━━━━━━━━━━━━━━━━"]
    owners = list_owners()
    for uid in owners:
        marker = " (настоящий)" if uid in CREATOR_IDS else ""
        lines.append(f"• {mention(uid, vk)}{marker}")
    send(peer_id, "\n".join(lines))

# ============================================================
#  ОБЩЕЕ
# ============================================================

def cmd_staff(user_id, peer_id, args, send, vk=None):
    cursor.execute('SELECT user_id, rank FROM users WHERE rank > 0 ORDER BY rank DESC')
    rows = cursor.fetchall()
    lines = ["👥 Персонал:\n"]
    current_rank = None
    for r in rows:
        if r['rank'] != current_rank:
            current_rank = r['rank']
            lines.append(f"\n{RANK_NAMES.get(current_rank, current_rank)} ({current_rank}):")
        lines.append(f"  {mention(r['user_id'], vk)}")
    send(peer_id, "\n".join(lines) if len(lines) > 1 else "📋 Нет персонала.")

def cmd_top(user_id, peer_id, args, send, vk=None):
    currency = 'RU'
    if args and args[0].upper() in ('RU', 'US', 'DE', 'JP', 'CN'):
        currency = args[0].upper()
    cursor.execute(
        f'SELECT user_id, balance_{currency} AS bal FROM users WHERE registered = 1 ORDER BY bal DESC LIMIT 10'
    )
    rows = cursor.fetchall()
    if not rows:
        send(peer_id, "📋 Нет данных.")
        return
    medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    lines = [f"🏆 Топ по {currency}:\n"]
    for i, r in enumerate(rows):
        lines.append(f"{medals[i]} {mention(r['user_id'], vk)} — {r['bal']:,}".replace(',', ' '))
    send(peer_id, "\n".join(lines))

def cmd_stats(user_id, peer_id, args, send, vk=None):
    target = user_id
    if args:
        target = parse_user_id(args[0], vk) or user_id
    u = get_user(target)
    cursor.execute('SELECT COUNT(*) FROM warns WHERE user_id = ?', (target,))
    warns = cursor.fetchone()[0]
    g = get_global_role(target)
    txt = (f"📊 Статистика {mention(target, vk)}\n"
           f"Ранг: {RANK_NAMES.get(u['rank'], 'Участник')}\n")
    if g:
        txt += f"🌐 Глобальная роль: {GLOBAL_ROLES.get(g, g)} ({g})\n"
    if is_real_creator(target):
        txt += "👑 Настоящий создатель\n"
    txt += (f"Уровень: {u['level']} (XP: {u['xp']})\n"
            f"Сообщений: {u['messages_total']}\n"
            f"Предупреждений: {warns}")
    send(peer_id, txt)

def cmd_help(user_id, peer_id, args, send, vk=None):
    send(peer_id, (
        "📖 СПИСОК КОМАНД\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 ОБЩИЕ (для всех)\n"
        "• !staff — персонал бота\n"
        "• !top [валюта] — топ игроков\n"
        "• !stats [id] — статистика\n"
        "• !rules — правила чата\n"
        "• !myrole — моя роль\n"
        "• !help — эта справка\n\n"
        "🎫 ТИКЕТЫ\n"
        "• !ticket [текст] — создать (0+)\n"
        "• !tickets — открытые (80+)\n"
        "• !answer [id] [текст] — ответ (80+)\n\n"
        "🛡 МОДЕРАЦИЯ\n"
        "• !roles — список ролей (5+)\n"
        "• !setnick [id] [ник] — сменить ник (5+)\n"
        "• !mute [id] [мин] — мут (10+)\n"
        "• !unmute [id] — снять мут (10+)\n"
        "• !warn [id] [причина] — варн (10+)\n"
        "• !warns [id] — список варнов (10+)\n"
        "• !унварн [id] [номер] — снять варн (10+)\n"
        "• !ban [id] [причина] — бан (20+)\n"
        "• !unban [id] — снять бан (20+)\n"
        "• !clear_warns [id] — снять все варны (50+)\n"
        "• !welcome [текст] — приветствие (66+)\n"
        "• !setrule [текст] — добавить правило (70+)\n"
        "• !delrule [номер] — удалить правило (70+)\n\n"
        "🛠 ТЕХ. АДМИН (глобальная роль 90)\n"
        "• !ping — проверить связь\n"
        "• !logs — последние ло


ги\n"
        "• !отчёт — отчёт за 24 часа\n\n"
        "🔥 СОЗДАТЕЛЬ (100)\n"
        "• !announce [текст] — рассылка\n"
        "• !globalban [id] [причина]\n"
        "• !unglobalban [id]\n"
        "• !chatlist — список бесед\n"
        "• !setrole [id] [ранг]\n"
        "• !gived [id] [сумма] [валюта] — выдать деньги\n"
        "• !gstaff — список глобального персонала\n"
        "• !addglobal [id] [80/90/100] — выдать глобальную роль\n"
        "• !delglobal [id] — снять глобальную роль\n\n"
        "👑 УПРАВЛЕНИЕ СОЗДАТЕЛЯМИ (только настоящий)\n"
        "• !owners — список создателей\n"
        "• !addowner [id] — сделать создателем\n"
        "• !delowner [id] — снять создателя\n\n"
        "💰 ЭКОНОМИКА\n"
        "• !старт [код] — регистрация\n"
        "• !профиль — мой профиль\n"
        "• !баланс — все кошельки\n"
        "• !дейли — бонус раз в 24ч\n"
        "• !перевод [id] [сумма] — перевод\n"
        "• !вклад [сумма] — в банк\n"
        "• !снять [сумма] — из банка\n"
        "• !обмен [сумма] [откуда] [куда]\n\n"
        "🌍 СТРАНЫ\n"
        "• !страна — моя страна\n"
        "• !казна — казна страны\n"
        "• !казна выдать [id] [сумма] — глава\n"
        "• !глава [id] [код] — назначить (создатель)\n"
        "• !глава снять [код] — снять (создатель)\n"
        "• !топстран — топ стран\n\n"
        "💼 РАБОТЫ\n"
        "• !работы — список работ\n"
        "• !устроиться [код] — устроиться\n"
        "• !работа — отработать смену\n\n"
        "🏠 ДОМА\n"
        "• !дома — каталог домов\n"
        "• !дом купить [lvl] — купить\n"
        "• !дом — инфо о моём доме\n"
        "• !дом доход — собрать доход\n"
        "• !сейф положить [сумма]\n"
        "• !сейф снять [сумма]\n\n"
        "🛒 МАГАЗИН\n"
        "• !магазин [phone/accessory/car]\n"
        "• !купить [код] — купить товар\n"
        "• !инвентарь — мои вещи\n"
        "• !звонок [id] — позвонить\n"
        "• !перезвонить [id]\n\n"
        "🏴 БАНДЫ\n"
        "• !банда — инфо о моей банде\n"
        "• !банда создать [имя] [тег]\n"
        "• !банда пригласить [id]\n"
        "• !банда выйти\n"
        "• !банда кик [id]\n"
        "• !банда повысить [id] [роль]\n"
        "• !банда вклад [сумма]\n"
        "• !банда топ\n\n"
        "💰 ОГРАБЛЕНИЯ\n"
        "• !ограбить [id] — ограбить игрока\n"
        "• !тюрьма [id] — кто в тюрьме\n"
        "• !штраф [id] [сумма] — полиция"
    ))

def cmd_ping(user_id, peer_id, args, send, vk=None):
    if not is_tech_admin(user_id):
        send(peer_id, "❌ Только Тех. Админ (90) / Владелец бота (100).")
        return
    start = time.time()
    try:
        vk.users.get(user_ids=1)
        ping = round((time.time() - start) * 1000, 2)
        send(peer_id, f"🏓 Понг! ({ping} мс)")
    except Exception as e:
        send(peer_id, f"❌ Ошибка: {e}")

def cmd_report(user_id, peer_id, args, send, vk=None):
    if not is_tech_admin(user_id):
        send(peer_id, "❌ Только тех. админ / владелец / создатель.")
        return
    text = _build_report_text(vk)
    send(peer_id, text)

def _build_report_text(vk=None):
    from db import get_daily_stats
    s = get_daily_stats(24)
    lines = [
        "📊 ОТЧЁТ ЗА 24 ЧАСА",
        "━━━━━━━━━━━━━━━━━━━━━\n",
        f"👥 Новых игроков: {s['new_users']}",
        f"📨 Сообщений (всего): {s['messages_total']:,}".replace(',', ' '),
        f"🔨 Мутов: {s['mutes']}",
        f"⛔ Банов: {s['bans']}",
        f"⚠️ Варнов: {s['warns']}",
        f"🎫 Тикетов: {s['tickets']}",
        f"💰 В казну стран: {s['treasury']:,} ₽".replace(',', ' '),
        "\n━━━ ДЕТАЛИ ━━━",
    ]
    if s['mutes_list']:
        lines.append("\n🔨 Последние муты:")
        for m in s['mutes_list']:
            lines.append(f"• {m['action']} ({m['timestamp'][11:16]})")
    if s['bans_list']:
        lines.append("\n⛔ Последние баны:")
        for b in s['bans_list']:
            lines.append(f"• {b['action']} ({b['timestamp'][11:16]})")
    if s['warns_list']:
        lines.append(


"\n⚠️ Последние варны:")
        for w in s['warns_list']:
            lines.append(f"• {mention(w['user_id'], vk)}: {w['reason']}")
    if len(lines) <= 10:
        lines.append("\n📋 Деталей за сутки нет.")
    return "\n".join(lines)
