import re
import time
import inspect
import threading
import datetime
import logging
import sys
import python
from python.longpoll import VkLongPoll, VkEventType

from config import TOKEN, CREATOR_IDS, BOT_GROUP_ID, LOG_PATH
from db import init_db, cursor, conn, get_user, list_global_roles
from utils import (
    send_message as _send, delete_message, kick_user_from_chat,
    extract_chat_id, is_muted, is_arrested, check_ban, is_global_banned,
    add_message_stat
)

from start import cmd_start
import economy
import countries
import jobs
import houses
import shop
import gangs
import robbery
import moderation


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)


def send(peer_id, text):
    _send(vk, peer_id, text)


def _house_router(user_id, peer_id, args, send, vk=None, msg_id=None):
    if not args:
        return houses.cmd_house_info(user_id, peer_id, [], send, vk)
    sub = args[0].lower()
    rest = args[1:]
    if sub == 'купить':
        return houses.cmd_house_buy(user_id, peer_id, rest, send)
    if sub == 'доход':
        return houses.cmd_house_collect(user_id, peer_id, rest, send)
    return houses.cmd_house_info(user_id, peer_id, args, send, vk)


def _safe_router(user_id, peer_id, args, send, vk=None, msg_id=None):
    if not args:
        send(peer_id, "📌 сейф положить [сумма]\n📌 сейф снять [сумма]")
        return
    sub = args[0].lower()
    rest = args[1:]
    if sub in ('положить', 'вклад', 'deposit'):
        return houses.cmd_safe_deposit(user_id, peer_id, rest, send)
    if sub in ('снять', 'вывести', 'withdraw'):
        return houses.cmd_safe_withdraw(user_id, peer_id, rest, send)
    send(peer_id, "📌 сейф положить/снять [сумма]")


def _gang_router(user_id, peer_id, args, send, vk=None, msg_id=None):
    if not args:
        return gangs.cmd_gang(user_id, peer_id, [], send, vk)
    sub = args[0].lower()
    rest = args[1:]
    if sub in ('создать', 'create'):
        return gangs.cmd_gang_create(user_id, peer_id, rest, send, vk)
    if sub in ('пригласить', 'invite'):
        return gangs.cmd_gang_invite(user_id, peer_id, rest, send, vk)
    if sub in ('выйти', 'leave'):
        return gangs.cmd_gang_leave(user_id, peer_id, rest, send)
    if sub in ('кик', 'kick'):
        return gangs.cmd_gang_kick(user_id, peer_id, rest, send, vk)
    if sub in ('повысить', 'promote'):
        return gangs.cmd_gang_promote(user_id, peer_id, rest, send, vk)
    if sub in ('вклад', 'deposit'):
        return gangs.cmd_gang_deposit(user_id, peer_id, rest, send)
    if sub in ('топ', 'top'):
        return gangs.cmd_gang_top(user_id, peer_id, rest, send)
    return gangs.cmd_gang(user_id, peer_id, [], send, vk)


def _country_router(user_id, peer_id, args, send, vk=None, msg_id=None):
    if args:
        sub = args[0].lower()
        if sub in ('выдать', 'give'):
            return countries.cmd_treasury_give(user_id, peer_id, args[1:], send, vk)
        if sub in ('снять', 'unset', 'убрать'):
            return countries.cmd_unsetleader(user_id, peer_id, args[1:], send, vk)
    return countries.cmd_treasury(user_id, peer_id, args, send, vk)


COMMANDS = {
    'staff': moderation.cmd_staff, 'стафф': moderation.cmd_staff,
    'top': moderation.cmd_top, 'топ': moderation.cmd_top,
    'stats': moderation.cmd_stats, 'stat': moderation.cmd_stats,
    'стат': moderation.cmd_stats, 'стата': moderation.cmd_stats,
    'статистика': moderation.cmd_stats,
    'rules': moderation.cmd_rules, 'правила': moderation.cmd_rules,
    'myrole': moderation.cmd_myrole, 'мояроль': moderation.cmd_myrole,
    'help': moderation.cmd_help, 'mhelp': moderation.cmd_help,
    'хелп': moderation.cmd_help, 'мхелп': moderation.cmd_help,
    'помощь': moderation.cmd_help,

    'ticket': moderation.cmd_ticket, 'тикет': moderation.cmd_ticket,
    'tickets': moderation.cmd_tickets, 'тикеты': moderation.cmd_tickets,
    'answer': moderation.cmd_answer, 'ответ': moderation.cmd_answer,

    'roles': moderation.cmd_roles, 'роли': moderation.cmd_roles,
    'setnick': moderation.cmd_setnick, 'ник': moderation.cmd_setnick,
    'mute': moderation.cmd_mute, 'мут': moderation.cmd_mute,
    'unmute': moderation.cmd_unmute, 'размут': moderation.cmd_unmute,
    'унмут': moderation.cmd_unmute,
    'warn': moderation.cmd_warn, 'пред': moderation.cmd_warn,
    'варн': moderation.cmd_warn, 'предупреждение': moderation.cmd_warn,
    'warns': moderation.cmd_warns, 'преды': moderation.cmd_warns,
    'унварн': moderation.cmd_unwarn, 'unwarn': moderation.cmd_unwarn,
    'ban': moderation.cmd_ban, 'бан': moderation.cmd_ban,
    'unban': moderation.cmd_unban, 'разбан': moderation.cmd_unban,
    'унбан': moderation.cmd_unban,
    'clear_warns': moderation.cmd_clear_warns, 'снять_преды': moderation.cmd_clear_warns,
    'снять_варны': moderation.cmd_clear_warns,
    'welcome': moderation.cmd_welcome, 'приветствие': moderation.cmd_welcome,
    'setrule': moderation.cmd_setrule, '+правило': moderation.cmd_setrule,
    'delrule': moderation.cmd_delrule, '-правило': moderation.cmd_delrule,

    'announce': moderation.cmd_announce, 'обьявление': moderation.cmd_announce,
    'объявление': moderation.cmd_announce,
    'ping': moderation.cmd_ping, 'пинг': moderation.cmd_ping,
    'logs': moderation.cmd_logs, 'логи': moderation.cmd_logs,
    'отчёт': moderation.cmd_report, 'отчет': moderation.cmd_report,
    'report': moderation.cmd_report,
    'globalban': moderation.cmd_globalban, 'gban': moderation.cmd_globalban,
    'глобалбан': moderation.cmd_globalban, 'гбан': moderation.cmd_globalban,
    'unglobalban': moderation.cmd_unglobalban, 'ungban': moderation.cmd_unglobalban,
    'снятьгбан': moderation.cmd_unglobalban, 'унгбан': moderation.cmd_unglobalban,
    'chatlist': moderation.cmd_chatlist, 'чатлист': moderation.cmd_chatlist,
    'setrole': moderation.cmd_setrole, '+роль': moderation.cmd_setrole,
    'выдать_роль': moderation.cmd_setrole,

    'addglobal': moderation.cmd_addglobal, 'addg': moderation.cmd_addglobal,
    'delglobal': moderation.cmd_delglobal, 'delg': moderation.cmd_delglobal,
    'gstaff': moderation.cmd_gstaff, 'гстафф': moderation.cmd_gstaff,

    'addowner': moderation.cmd_addowner, 'addo': moderation.cmd_addowner,
    'delowner': moderation.cmd_delowner, 'delo': moderation.cmd_delowner,
    'owners': moderation.cmd_owners,

    'старт': cmd_start, 'start': cmd_start,
    'профиль': economy.cmd_profile, 'пр': economy.cmd_profile,
    'profile': economy.cmd_profile,
    'баланс': economy.cmd_balance, 'бал': economy.cmd_balance,
    'balance': economy.cmd_balance,
    'дейли': economy.cmd_daily, 'daily': economy.cmd_daily,
    'перевод': economy.cmd_transfer, 'transfer': economy.cmd_transfer,
    'вклад': economy.cmd_deposit, 'deposit': economy.cmd_deposit,
    'снять': economy.cmd_withdraw, 'withdraw': economy.cmd_withdraw,
    'обмен': economy.cmd_exchange, 'exchange': economy.cmd_exchange,
    'gived': economy.cmd_gived, 'выдать': economy.cmd_gived,

    'страна': countries.cmd_country,
    'глава': countries.cmd_setleader,
    'топстран': countries.cmd_top_countries,

    'работы': jobs.cmd_jobs, 'jobs': jobs.cmd_jobs,
    'устроиться': jobs.cmd_apply, 'apply': jobs.cmd_apply,
    'работа': jobs.cmd_work, 'work': jobs.cmd_work,

    'дома': houses.cmd_houses, 'houses': houses.cmd_houses,

    'магазин': shop.cmd_shop, 'shop': shop.cmd_shop,
    'купить': shop.cmd_buy, 'buy': shop.cmd_buy,
    'инвентарь': shop.cmd_inventory, 'inv': shop.cmd_inventory,
    'звонок': shop.cmd_call, 'call': shop.cmd_call,
    'перезвонить': shop.cmd_callback,

    'ограбить': robbery.cmd_rob, 'rob': robbery.cmd_rob,
    'тюрьма': robbery.cmd_arrest_info, 'jail': robbery.cmd_arrest_info,
    'штраф': robbery.cmd_police_fine, 'fine': robbery.cmd_police_fine,
}


COMMANDS['дом'] = _house_router
COMMANDS['house'] = _house_router
COMMANDS['сейф'] = _safe_router
COMMANDS['safe'] = _safe_router
COMMANDS['банда'] = _gang_router
COMMANDS['gang'] = _gang_router
COMMANDS['казна'] = _country_router


def process_command(user_id, peer_id, text, msg_id=None):
    text = re.sub(r'\[club\d+\|@?\w+\]\s*', '', text, flags=re.IGNORECASE).strip()
    if not text or text[0] not in ['!', '/']:
        return
    text = text[1:].strip()
    parts = text.split()
    if not parts:
        return
    cmd = parts[0].lower()
    args = parts[1:]
    handler = COMMANDS.get(cmd)
    if not handler:
        return
    try:
        sig = inspect.signature(handler)
        params = sig.parameters
        kwargs = {}
        if 'vk' in params:
            kwargs['vk'] = vk
        if 'msg_id' in params:
            kwargs['msg_id'] = msg_id
        handler(user_id, peer_id, args, send, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка обработки {cmd}: {e}")
        send(peer_id, f"❌ Ошибка: {e}")


def handle_invite(peer_id, invited_id):
    if invited_id and invited_id > 0:
        get_user(invited_id)
    if invited_id == -BOT_GROUP_ID:
        cursor.execute('INSERT OR IGNORE INTO chats (peer_id) VALUES (?)', (peer_id,))
        conn.commit()
        send(peer_id, "✅ Бот добавлен. Нужны права администратора.")
        logger.info(f"Бот добавлен в {peer_id}")
        return
    if peer_id > 2_000_000_000:
        cursor.execute('INSERT OR IGNORE INTO chats (peer_id) VALUES (?)', (peer_id,))
        conn.commit()
    if invited_id > 0 and is_global_banned(invited_id):
        chat_id = extract_chat_id(peer_id)
        if chat_id and kick_user_from_chat(vk, chat_id, invited_id):
            from utils import mention
            cursor.execute('SELECT reason FROM global_bans WHERE user_id = ?', (invited_id,))
            row = cursor.fetchone()
            reason = row['reason'] if row else 'Не указана'
            send(peer_id, f"⛔ {mention(invited_id, vk)} в глобальном бане.\n📄 {reason}")


def daily_report_worker():
    from config import REPORT_HOUR, REPORT_MINUTE, CREATOR_IDS
    while True:
        try:
            now = datetime.datetime.now()
            target = now.replace(hour=REPORT_HOUR, minute=REPORT_MINUTE, second=0, microsecond=0)
            if target <= now:
                target += datetime.timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            logger.info(f"⏰ Следующий автоотчёт через {int(wait_seconds//3600)}ч {int((wait_seconds%3600)//60)}мин")
            time.sleep(wait_seconds)
            text = moderation._build_report_text(vk)
            recipients = set(CREATOR_IDS)
            for r in list_global_roles():
                if r['role_level'] >= 90:
                    recipients.add(r['user_id'])
            for uid in recipients:
                try:
                    send(uid, text)
                    time.sleep(0.3)
                except Exception as e:
                    logger.error(f"Отчёт не ушёл {uid}: {e}")
            logger.info(f"📊 Автоотчёт отправлен {len(recipients)} админам")
        except Exception as e:
            logger.error(f"Ошибка автоотчёта: {e}")
            time.sleep(60)


def main():
    global vk, vk_session, longpoll
    init_db()
    logger.info(f"✅ Бот запущен. Создатели: {CREATOR_IDS}")
    threading.Thread(target=daily_report_worker, daemon=True).start()
    logger.info("⏰ Поток автоотчёта запущен")
    while True:
        try:
            logger.info("🔄 Подключение к LongPoll...")
            for event in longpoll.listen():
                if event.type != VkEventType.MESSAGE_NEW:
                    continue
                action = getattr(event, 'action', None)
                if action and isinstance(action, dict):
                    atype = action.get('type')
                    if atype == 'chat_invite_user':
                        handle_invite(event.peer_id, action.get('member_id'))
                        continue
                    if atype == 'chat_kick_user':
                        continue
                if not event.to_me:
                    continue
                user_id = event.user_id
                peer_id = event.peer_id
                text = event.text or ''
                msg_id = event.message_id
                if not user_id:
                    continue
                get_user(user_id)
                if peer_id > 2_000_000_000:
                    cursor.execute('INSERT OR IGNORE INTO chats (peer_id) VALUES (?)', (peer_id,))
                    conn.commit()
                if check_ban(user_id):
                    delete_message(vk, peer_id, msg_id)
                    continue
                if is_arrested(user_id):
                    t = (text or '').strip()
                    if t.startswith(('!', '/')):
                        cmd_word = t[1:].strip().split()[0].lower() if t[1:].strip() else ''
                        if cmd_word not in ('тюрьма', 'jail'):
                            delete_message(vk, peer_id, msg_id)
                            send(peer_id, "🚔 Вы сидите в тюрьме. Ничего делать нельзя.")
                            continue
                    else:
                        delete_message(vk, peer_id, msg_id)
                        send(peer_id, "🚔 Вы сидите в тюрьме.")
                        continue
                if is_muted(user_id):
                    delete_message(vk, peer_id, msg_id)
                    continue
                add_message_stat(user_id)
                try:
                    logger.info(f"MSG {user_id}: {text}")
                    process_command(user_id, peer_id, text, msg_id)
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
        except Exception as e:
            logger.error(f"💥 LongPoll упал: {type(e).__name__}: {e}")
            logger.info("⏳ Переподключение через 10 секунд...")
            time.sleep(10)
            try:
                vk_session = vk_api.VkApi(token=TOKEN)
                vk = vk_session.get_api()
                longpoll = VkLongPoll(vk_session)
                logger.info("🔄 Пересоздано подключение к VK")
            except Exception as e2:
                logger.error(f"❌ Не удалось пересоздать: {e2}")
                time.sleep(20)


if __name__ == '__main__':
    main()
