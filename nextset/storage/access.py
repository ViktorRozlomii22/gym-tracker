"""Invitation membership. Plain invitation secrets are returned only at creation."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import nextset.storage.database as db


def ensure_schema(connection):
    connection.executescript('''
        CREATE TABLE IF NOT EXISTS members(user_id INTEGER PRIMARY KEY, joined_at TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS invitations(id INTEGER PRIMARY KEY, digest TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL, created_by INTEGER NOT NULL, used_by INTEGER, revoked INTEGER NOT NULL DEFAULT 0);
    ''')


def is_admin(uid):
    owner = db.setting('owner')
    return owner is not None and owner == uid


def require_admin(uid):
    if not is_admin(uid):
        raise ValueError('Ця дія доступна лише адміністратору.')


def allowed(uid):
    if is_admin(uid):
        return True
    with db.connection() as connection:
        row = connection.execute('SELECT active FROM members WHERE user_id=?', (uid,)).fetchone()
    return bool(row and row['active'])


def require_ai(uid):
    if not is_admin(uid):
        raise ValueError('ШІ зараз доступний лише адміністратору. Щоденник, нотатки, виміри й графіки працюють без ШІ.')


def create_invite(uid, now=None):
    require_admin(uid)
    now = now or datetime.now(timezone.utc)
    token = secrets.token_urlsafe(24)
    digest = hashlib.sha256(token.encode()).hexdigest()
    with db.connection() as connection:
        cursor = connection.execute('INSERT INTO invitations(digest,expires_at,created_by) VALUES (?,?,?)',
            (digest, (now + timedelta(days=7)).isoformat(), uid))
    return cursor.lastrowid, token


def redeem(uid, token, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(token, str) or not 20 <= len(token) <= 64:
        return False
    digest = hashlib.sha256(token.encode()).hexdigest()
    with db.connection() as connection:
        connection.execute('BEGIN IMMEDIATE')
        member = connection.execute('SELECT active FROM members WHERE user_id=?', (uid,)).fetchone()
        # A blocked account cannot evade the block with another invitation.
        if member or is_admin(uid):
            return False
        invitation = connection.execute('SELECT * FROM invitations WHERE digest=? AND used_by IS NULL AND revoked=0', (digest,)).fetchone()
        if not invitation or datetime.fromisoformat(invitation['expires_at']) <= now:
            return False
        connection.execute('INSERT INTO members(user_id,joined_at) VALUES (?,?)', (uid, now.isoformat()))
        connection.execute('UPDATE invitations SET used_by=? WHERE id=?', (uid, invitation['id']))
    return True


def revoke_invite(uid, identifier):
    require_admin(uid)
    with db.connection() as connection:
        return bool(connection.execute('UPDATE invitations SET revoked=1 WHERE id=? AND used_by IS NULL AND revoked=0', (identifier,)).rowcount)


def list_members(uid):
    require_admin(uid)
    with db.connection() as connection:
        return [dict(row) for row in connection.execute('SELECT user_id,joined_at,active FROM members ORDER BY joined_at DESC')]


def set_active(uid, target, active):
    require_admin(uid)
    if is_admin(target):
        raise ValueError('Доступ адміністратора не можна заблокувати цією командою.')
    with db.connection() as connection:
        changed = connection.execute('UPDATE members SET active=? WHERE user_id=?', (int(active), target)).rowcount
    if not changed:
        raise ValueError('Такого учасника немає.')


def recipients():
    with db.connection() as connection:
        users = {row[0] for row in connection.execute('SELECT user_id FROM members WHERE active=1')}
    owner = db.setting('owner')
    if owner is not None:
        users.add(owner)
    return sorted(users)
