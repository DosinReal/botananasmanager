import sqlite3
import datetime
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()


def init_db():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id         INTEGER PRIMARY KEY,
            rank            INTEGER DEFAULT 0,
            nickname        TEXT    DEFAULT '',
            balance_RU      INTEGER DEFAULT 0,
            balance_US      INTEGER DEFAULT 0,
            balance_DE      INTEGER DEFAULT 0,
            balance_JP      INTEGER DEFAULT 0,
            balance_CN      INTEGER DEFAULT 0,
            bank            INTEGER DEFAULT 0,
            safe            INTEGER DEFAULT 0,
            level           INTEGER DEFAULT 1,
            xp              INTEGER DEFAULT 0,
            country         TEXT,
            city            TEXT,
            registered      INTEGER DEFAULT 0,
            job             TEXT,
            job_cooldown    TEXT,
            business        INTEGER DEFAULT 0,
            business_ts     TEXT,
            house_level     INTEGER DEFAULT 0,
            house_ts        TEXT,
            gang_id         INTEGER,
            gang_role       TEXT,
            mute_until      TEXT,
            arrest_until    TEXT,
            rob_cooldown    TEXT,
            last_daily      TEXT,
            messages_total  INTEGER DEFAULT 0,
            created_at      TEXT
        )
    ''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS countries (
        code TEXT PRIMARY KEY, name TEXT, currency TEXT, rate INTEGER,
        emoji TEXT, treasury INTEGER DEFAULT 0, leader_id INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS gangs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, tag TEXT,
        leader_id INTEGER, treasury INTEGER DEFAULT 0, created_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        item_code TEXT, bought_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
        currency TEXT, type TEXT, note TEXT, timestamp TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS bans
        (user_id INTEGER PRIMARY KEY, reason TEXT, timestamp TEXT, admin_id INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS mutes
        (user_id INTEGER PRIMARY KEY, until TEXT, reason TEXT, admin_id INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS warns
        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, reason TEXT,
         moderator_id INTEGER, timestamp TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs
        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, timestamp TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS global_bans
        (user_id INTEGER PRIMARY KEY, reason TEXT, timestamp TEXT, admin_id INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS chats (peer_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tickets
        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT,
         status TEXT DEFAULT 'open', timestamp TEXT,
         answer TEXT DEFAULT '', answered_by INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS rules
        (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS welcome_settings
        (peer_id INTEGER PRIMARY KEY, message TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS global_roles (
        user_id INTEGER PRIMARY KEY,
        role_level INTEGER NOT NULL,
        granted_by INTEGER,
        granted_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS owners (
        user_id INTEGER PRIMARY KEY,
        added_by INTEGER,
        added_at TEXT)''')
    conn.commit()
    _seed_countries()
    logger.info("БД инициализирована")


def _seed_countries():
    from config import COUNTRIES
    for code, name, currency, rate, emoji in COUNTRIES:
        cursor.execute('''INSERT OR IGNORE INTO countries
            (code, name, currency, rate, emoji) VALUES (?, ?, ?, ?, ?)''',
            (code, name, currency, rate, emoji))
    conn.commit()


def now_iso():
    return datetime.datetime.now().isoformat()


def get_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute('''INSERT INTO users
            (user_id, rank, nickname, level, messages_total, created_at)
            VALUES (?, 0, '', 1, 0, ?)''', (user_id, now_iso()))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
    return dict(row)


def update_user(user_id, **kwargs):
    get_user(user_id)
    if not kwargs:
        return
    fields = ', '.join(f'{k} = ?' for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    cursor.execute(f'UPDATE users SET {fields} WHERE user_id = ?', values)
    conn.commit()


def add_xp(user_id, amount):
    from config import XP_PER_LEVEL
    u = get_user(user_id)
    xp = (u.get('xp') or 0) + amount
    level = u.get('level') or 1
    leveled_up = False
    while xp >= XP_PER_LEVEL:
        xp -= XP_PER_LEVEL
        level += 1
        leveled_up = True
    update_user(user_id, xp=xp, level=level)
    return level, leveled_up


def get_balance(user_id, currency='RU'):
    u = get_user(user_id)
    return u.get(f'balance_{currency}', 0) or 0


def add_balance(user_id, amount, currency='RU', note='', tx_type='other'):
    u = get_user(user_id)
    field = f'balance_{currency}'
    new_val = max(0, (u.get(field) or 0) + amount)
    update_user(user_id, **{field: new_val})
    cursor.execute('''INSERT INTO transactions
        (user_id, amount, currency, type, note, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (user_id, amount, currency, tx_type, note, now_iso()))
    conn.commit()
    return new_val


def log_action(user_id, action):
    cursor.execute('INSERT INTO logs (user_id, action, timestamp) VALUES (?, ?, ?)',
                   (user_id, action, now_iso()))
    conn.commit()


# ---------- Глобальные роли ----------

def get_global_role(user_id):
    cursor.execute('SELECT role_level FROM global_roles WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    return row['role_level'] if row else 0


def set_global_role(user_id, level, granted_by):
    cursor.execute('''INSERT OR REPLACE INTO global_roles
        (user_id, role_level, granted_by, granted_at) VALUES (?, ?, ?, ?)''',
        (user_id, level, granted_by, now_iso()))
    conn.commit()


def remove_global_role(user_id):
    cursor.execute('DELETE FROM global_roles WHERE user_id = ?', (user_id,))
    conn.commit()


def list_global_roles():
    cursor.execute('SELECT user_id, role_level FROM global_roles ORDER BY role_level DESC')
    return [dict(r) for r in cursor.fetchall()]


# ---------- Создатели (несколько) ----------

def add_owner(user_id, added_by):
    cursor.execute('''INSERT OR IGNORE INTO owners
        (user_id, added_by, added_at) VALUES (?, ?, ?)''',
        (user_id, added_by, now_iso()))
    conn.commit()


def remove_owner(user_id):
    cursor.execute('DELETE FROM owners WHERE user_id = ?', (user_id,))
    conn.commit()


def is_owner_db(user_id):
    from config import CREATOR_IDS
    if user_id in CREATOR_IDS:
        return True
    cursor.execute('SELECT 1 FROM owners WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None


def list_owners():
    from config import CREATOR_IDS
    result = list(CREATOR_IDS)
    cursor.execute('SELECT user_id FROM owners ORDER BY added_at')
    for r in cursor.fetchall():
        if r['user_id'] not in result:
            result.append(r['user_id'])
    return result


# ---------- Отчёт ----------

def get_daily_stats(hours=24):
    import datetime as _dt
    since = (_dt.datetime.now() - _dt.timedelta(hours=hours)).isoformat()
    stats = {}

    cursor.execute('SELECT COUNT(*) FROM users WHERE registered = 1 AND created_at >= ?', (since,))
    stats['new_users'] = cursor.fetchone()[0]

    cursor.execute('SELECT COALESCE(SUM(messages_total), 0) FROM users')
    stats['messages_total'] = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM logs WHERE action LIKE "Мут%" AND timestamp >= ?', (since,))
    stats['mutes'] = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM logs WHERE action LIKE "Бан%" AND timestamp >= ?', (since,))
    stats['bans'] = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM warns WHERE timestamp >= ?', (since,))
    stats['warns'] = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM tickets WHERE timestamp >= ?', (since,))
    stats['tickets'] = cursor.fetchone()[0]

    cursor.execute('SELECT COALESCE(SUM(treasury), 0) FROM countries')
    stats['treasury'] = cursor.fetchone()[0]

    cursor.execute('SELECT user_id, action, timestamp FROM logs WHERE action LIKE "Мут%" AND timestamp >= ? ORDER BY id DESC LIMIT 10', (since,))
    stats['mutes_list'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute('SELECT user_id, action, timestamp FROM logs WHERE action LIKE "Бан%" AND timestamp >= ? ORDER BY id DESC LIMIT 10', (since,))
    stats['bans_list'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute('SELECT user_id, reason, moderator_id, timestamp FROM warns WHERE timestamp >= ? ORDER BY id DESC LIMIT 10', (since,))
    stats['warns_list'] = [dict(r) for r in cursor.fetchall()]

    return stats