import datetime
from config import JOBS, to_currency, currency_symbol, XP_PER_SHIFT, to_rub
from db import get_user, update_user, now_iso, add_xp
from economy import apply_tax_and_pay


def cmd_jobs(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    lines = ["💼 Работы:\n"]
    for code, j in JOBS.items():
        if j.get('buy_price_rub'):
            price_local = to_currency(j['buy_price_rub'], u['country'])
            sym = currency_symbol(u['country'])
            lines.append(f"• {j['name']} — код: {code} (купить {price_local:,} {sym})".replace(',', ' '))
        else:
            lines.append(f"• {j['name']} — код: {code} ({j['salary_rub']:,}₽)".replace(',', ' '))
    lines.append("\n📌 !устроиться [код]")
    send(peer_id, "\n".join(lines))


def cmd_apply(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    if not args:
        send(peer_id, "📌 устроиться [код]")
        return
    code = args[0].lower()
    if code not in JOBS:
        send(peer_id, "❌ Нет такой работы.")
        return
    j = JOBS[code]

    if code == 'business':
        if u['business']:
            send(peer_id, "❌ Уже есть бизнес.")
            return
        # платим в валюте страны
        country = u['country']
        price_local = to_currency(j['buy_price_rub'], country)
        sym = currency_symbol(country)
        bal = u.get(f'balance_{country}') or 0
        if bal < price_local:
            send(peer_id, f"❌ Нужно {price_local:,} {sym}. У тебя {bal:,} {sym}.".replace(',', ' '))
            return
        update_user(user_id,
                    **{f'balance_{country}': bal - price_local},
                    business=1, business_ts=now_iso())
        send(peer_id, f"✅ Бизнес куплен за {price_local:,} {sym}!".replace(',', ' '))
        return

    update_user(user_id, job=code, job_cooldown=None)
    send(peer_id, f"✅ Работа: {j['name']}")


def cmd_work(user_id, peer_id, args, send, vk=None, msg_id=None):
    u = get_user(user_id)
    if not u['registered']:
        send(peer_id, "❌ Сначала !старт")
        return
    if u['business']:
        return _collect_business(user_id, peer_id, u, send)
    if not u['job']:
        send(peer_id, "❌ Безработный. !работы")
        return
    code = u['job']
    j = JOBS.get(code)
    if u['job_cooldown']:
        cd = datetime.datetime.fromisoformat(u['job_cooldown'])
        if datetime.datetime.now() < cd:
            left = (cd - datetime.datetime.now()).total_seconds()
            send(peer_id, f"⏳ {int(left//60)}мин {int(left%60)}с")
            return
    net = apply_tax_and_pay(user_id, j['salary_rub'], note=f'смена {code}')
    cd = datetime.datetime.now() + datetime.timedelta(minutes=j['cooldown_minutes'])
    update_user(user_id, job_cooldown=cd.isoformat())

    lvl, up = add_xp(user_id, XP_PER_SHIFT)
    sym = currency_symbol(u['country'])
    txt = f"💼 {j['name']}\n💰 +{net:,} {sym}".replace(',', ' ')
    if up:
        txt += f"\n🎉 Новый уровень: {lvl}!"
    send(peer_id, txt)


def _collect_business(user_id, peer_id, u, send):
    if not u['business_ts']:
        update_user(user_id, business_ts=now_iso())
        send(peer_id, "✅ Таймер запущен.")
        return
    last = datetime.datetime.fromisoformat(u['business_ts'])
    hours = int((datetime.datetime.now() - last).total_seconds() // 3600)
    if hours < 1:
        send(peer_id, "⏳ Меньше часа.")
        return
    gross = JOBS['business']['hourly_income_rub'] * hours
    net = apply_tax_and_pay(user_id, gross, note=f'бизнес {hours}ч')
    update_user(user_id, business_ts=now_iso())

    lvl, up = add_xp(user_id, XP_PER_SHIFT * hours)
    sym = currency_symbol(u['country'])
    txt = f"💼 Бизнес {hours}ч\n💰 +{net:,} {sym}".replace(',', ' ')
    if up:
        txt += f"\n🎉 Новый уровень: {lvl}!"
    send(peer_id, txt)