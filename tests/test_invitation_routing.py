from types import SimpleNamespace
from unittest.mock import AsyncMock
from telegram.ext import ApplicationHandlerStop
from tests.test_access import Access
from nextset.storage import access
from nextset.telegram.runtime import guard
from nextset.telegram.access import route
import unittest


class InvitationRouting(Access, unittest.IsolatedAsyncioTestCase):
    def update(self, uid, text):
        return SimpleNamespace(effective_user=SimpleNamespace(id=uid), effective_chat=SimpleNamespace(type='private'),
            message=SimpleNamespace(text=text,reply_text=AsyncMock()))

    async def test_guard_admits_invited_user_only_once_and_blocks_group_access(self):
        _,token=access.create_invite(1)
        update=self.update(2,'/start invite_'+token)
        await guard(update,None)
        await guard(self.update(2,'/history'),None)
        with self.assertRaises(ApplicationHandlerStop):await guard(self.update(3,'/start invite_'+token),None)
        access.set_active(1,2,False)
        with self.assertRaises(ApplicationHandlerStop):await guard(update,None)
        update=self.update(1,'/start')
        update.effective_chat.type='group'
        with self.assertRaises(ApplicationHandlerStop):await guard(update,None)

    async def test_admin_invites_and_members_cannot_manage_access(self):
        context=SimpleNamespace(bot=SimpleNamespace(get_me=AsyncMock(return_value=SimpleNamespace(username='test_bot'))))
        update=self.update(1,'/invite')
        self.assertTrue(await route(update,context))
        self.assertIn('start=invite_',update.message.reply_text.call_args.args[0])
        update=self.update(2,'/invite')
        self.assertTrue(await route(update,context))
        self.assertIn('лише адміністратору',update.message.reply_text.call_args.args[0])
        self.assertEqual(context.bot.get_me.await_count,1)

    async def test_member_cannot_bypass_ai_restriction_with_commands_or_buttons(self):
        from nextset.telegram.access import AI_COMMANDS,AI_BUTTONS
        from nextset.coaching.jobs import begin
        _,token=access.create_invite(1)
        access.redeem(2,token)
        for text in [f'/{cmd}@test_bot: details' for cmd in AI_COMMANDS]+list(AI_BUTTONS):
            with self.subTest(text=text),self.assertRaises(ApplicationHandlerStop):
                await guard(self.update(2,text),None)
        with self.assertRaises(ValueError):await begin(self.update(2,'/ask hello'),None,'/ask','hello')
        await guard(self.update(2,'/history'),None)
        await guard(self.update(1,'/ask hello'),None)

    async def test_members_cannot_create_or_list_host_backups(self):
        from datetime import datetime
        from nextset.coaching.tools import handle
        from unittest.mock import patch
        for command in ('/backup','/backups'):
            with patch('nextset.storage.backups.create_backup',side_effect=AssertionError('must not run')):
                with self.assertRaises(ValueError):
                    await handle(self.update(2,command),None,command,'',{},datetime.now())

    async def test_member_home_and_account_do_not_offer_admin_or_ai_actions(self):
        from nextset.telegram.ui import home
        update=self.update(2,'/account')
        await route(update,None)
        self.assertIn('Telegram ID: 2',update.message.reply_text.call_args.args[0])
        await home(update,None)
        markup=str(update.message.reply_text.call_args.kwargs['reply_markup'])
        self.assertNotIn('Мій план',markup)
        self.assertNotIn('Учасники',markup)
        self.assertIn('Мій прогрес',markup)

    async def test_failed_invitation_delivery_revokes_only_new_unused_link(self):
        import nextset.storage.database as db
        _,existing=access.create_invite(1)
        context=SimpleNamespace(bot=SimpleNamespace(get_me=AsyncMock(return_value=SimpleNamespace(username='test_bot'))))
        update=self.update(1,'/invite')
        update.message.reply_text.side_effect=RuntimeError('delivery failed')
        with self.assertRaises(RuntimeError):
            await route(update,context)
        with db.connection() as connection:
            rows=connection.execute('SELECT revoked FROM invitations ORDER BY id').fetchall()
        self.assertEqual([row['revoked'] for row in rows],[0,1])
        self.assertTrue(access.redeem(2,existing))
