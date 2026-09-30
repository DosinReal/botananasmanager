from config import SHOP_ITEMS, to_currency, currency_symbol
from db import get_user, update_user, cursor, conn, now_iso


def cmd_shop(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    cat = args[0].lower() if args else None
    lines = ["🛒 Магазин:\n"]
    for code, item in SHOP_ITEMS.items():
        if cat and item['category'] != cat:
            continue
        price = to_currency(item['price_rub'], u['country'])
        sym = currency_symbol(u['country'])
        lines.append(f"• {item['name']} — {price:,} {sym} ({code})".replace(',', ' '))
    lines.append("\n📌 !купить [код]")
    send(peer_id, "\n".join(lines))


def cmd_buy(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    if not args:
        send(peer_id, "📌 купить [код]")
        return
    code = args[0].lower()
    if code not in SHOP_ITEMS:
        send(peer_id, "❌ Нет такого.")
        return
    item = SHOP_ITEMS[code]
    price_local = to_currency(item['price_rub'], u['country'])
    sym = currency_symbol(u['country'])
    bal = u.get(f'balance_{u["country"]}') or 0
    if bal < price_local:
        send(peer_id, f"❌ Нужно {price_local:,} {sym}".replace(',', ' '))
        return
    if item['category'] == 'phone':
        cursor.execute('DELETE FROM inventory WHERE user_id = ? AND item_code LIKE "phone_%"', (user_id,))
    update_user(user_id, **{f'balance_{u["country"]}': bal - price_local})
    cursor.execute('INSERT INTO inventory (user_id, item_code, bought_at) VALUES (?, ?, ?)',
                   (user_id, code, now_iso()))
    conn.commit()
    send(peer_id, f"✅ Куплено: {item['name']}")


def cmd_inventory(user_id, peer_id, args, send, vk=None, msg_id=None):
    cursor.execute('SELECT item_code FROM inventory WHERE user_id = ? ORDER BY id DESC', (user_id,))
    rows = cursor.fetchall()
    if not rows:
        send(peer_id, "🎒 Пусто.")
        return
    lines = ["🎒 Инвентарь:\n"]
    for r in rows:
        it = SHOP_ITEMS.get(r['item_code'], {})
        lines.append(f"• {it.get('name', r['item_code'])}")
    send(peer_id, "\n".join(lines))


def cmd_call(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import parse_user_id, mention
    if not args:
        send(peer_id, "📌 звонок [id]")
        return
    cursor.execute('SELECT 1 FROM inventory WHERE user_id = ? AND item_code LIKE "phone_%"', (user_id,))
    if not cursor.fetchone():
        send(peer_id, "❌ Нужен телефон.")
        return
    target = parse_user_id(args[0], vk)
    if not target or target == user_id:
        send(peer_id, "❌ Неверный ID.")
        return
    send(peer_id, f"📞 Звонишь {mention(target, vk)}")
    try:
        send(target, f"📞 Звонит {mention(user_id, vk)}")
    except Exception:
        pass


def cmd_callback(user_id, peer_id, args, send, vk=None, msg_id=None):
    from utils import parse_user_id, mention
    if not args:
        send(peer_id, "📌 перезвонить [id]")
        return
    cursor.execute('SELECT 1 FROM inventory WHERE user_id = ? AND item_code LIKE "phone_%"', (user_id,))
    if not cursor.fetchone():
        send(peer_id, "❌ Нужен телефон.")
        return
    target = parse_user_id(args[0], vk)
    if not target:
        send(peer_id, "❌ Неверный ID.")
        return
    send(peer_id, f"📞 Перезвонил {mention(target, vk)}")
    try:
        send(target, f"📞 {mention(user_id, vk)} перезвонил!")
    except Exception:
        pass