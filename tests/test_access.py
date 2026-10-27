from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
import nextset.storage.database as db
from nextset.storage import access


class Access(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        old=db.DB_PATH
        db.DB_PATH=Path(self.tmp.name)/'test.sqlite3'
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(setattr,db,'DB_PATH',old)
        db.ensure_bot_schema()
        db.set_setting('owner',1)

    def test_single_use_expiry_revocation_and_secret_storage(self):
        now=datetime(2026,10,23,tzinfo=timezone.utc)
        identifier,token=access.create_invite(1,now)
        self.assertTrue(access.redeem(2,token,now))
        self.assertFalse(access.redeem(3,token,now))
        self.assertTrue(access.allowed(2))
        with db.connection() as connection:
            self.assertNotEqual(connection.execute('SELECT digest FROM invitations WHERE id=?',(identifier,)).fetchone()[0],token)
        identifier,token=access.create_invite(1,now)
        self.assertFalse(access.redeem(3,token,now+timedelta(days=7)))
        self.assertTrue(access.revoke_invite(1,identifier))
        self.assertFalse(access.redeem(3,token,now))
        self.assertFalse(access.redeem(3,'wrong'))

    def test_admin_only_controls_and_block_cannot_be_evaded(self):
        _,token=access.create_invite(1)
        self.assertTrue(access.redeem(2,token))
        with self.assertRaises(ValueError):access.create_invite(2)
        with self.assertRaises(ValueError):access.list_members(2)
        with self.assertRaises(ValueError):access.require_ai(2)
        access.require_ai(1)
        access.set_active(1,2,False)
        self.assertFalse(access.allowed(2))
        _,token=access.create_invite(1)
        self.assertFalse(access.redeem(2,token))
        self.assertEqual(access.recipients(),[1])
        access.set_active(1,2,True)
        self.assertEqual(access.recipients(),[1,2])
        with self.assertRaises(ValueError):access.set_active(1,1,False)

    def test_pending_invitation_list_excludes_expired_used_revoked_and_secrets(self):
        now=datetime(2026,10,27,tzinfo=timezone.utc)
        pending,token=access.create_invite(1,now)
        access.create_invite(1,now-timedelta(days=7))
        used,used_token=access.create_invite(1,now)
        self.assertTrue(access.redeem(2,used_token,now))
        revoked,_=access.create_invite(1,now)
        access.revoke_invite(1,revoked)
        rows=access.list_invites(1,now)
        self.assertEqual([row['id'] for row in rows],[pending])
        self.assertEqual(set(rows[0]),{'id','expires_at'})
        self.assertNotIn(token,str(rows))
        with self.assertRaises(ValueError):access.list_invites(2,now)
