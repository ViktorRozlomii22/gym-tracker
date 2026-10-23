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
