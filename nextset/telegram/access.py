"""Admin controls and invitation admission; ordinary users never see host state."""
import re
from nextset.storage import access
from nextset.telegram.diary import send_chunks

HELP = ('👥 Учасники\n/invite — одноразове запрошення на 7 днів\n'
        '/members — учасники та їхні Telegram ID\n/invites — активні невикористані запрошення\n/revokeinvite номер — скасувати невикористане запрошення\n'
        '/blockuser ID — призупинити доступ\n/unblockuser ID — повернути доступ\n'
        'ШІ доступний лише адміністратору. Оплата не підключена.')

AI_COMMANDS = {'plan','block','extra','swap','ask','coach','coachconfirm','weeklyai',
               'ai','confirm','aistatus','airesult','aicancel','planconfirm','blockconfirm','swapconfirm'}
AI_BUTTONS = {'✨ Створити 8 тижнів','🏋️ Наступна сесія','📋 Мій план',
              '🧠 Стан ШІ','🛑 Скасувати ШІ','✅ Прийняти сесію','✅ Прийняти блок'}


async def allow_member_action(update):
    text = (update.message.text or '').strip()
    command = re.match(r'^/(\w+)(?:@\w+)?(?:\s|:|$)', text)
    if text in AI_BUTTONS or command and command[1].lower() in AI_COMMANDS:
        await update.message.reply_text('ШІ зараз доступний лише адміністратору. Ти можеш вести щоденник, додавати нотатки та виміри й переглядати власні графіки.')
        return False
    return True


async def route(update, context):
    text = update.message.text.strip()
    if text.split('@')[0]=='/account':
        admin=access.is_admin(update.effective_user.id)
        await update.message.reply_text(f'Твій Telegram ID: {update.effective_user.id}\nРоль: '+('адміністратор' if admin else 'запрошений учасник')+'\nШІ: '+('доступний' if admin else 'зараз лише для адміністратора')+'\nТренування, нотатки, виміри й експорт належать твоєму акаунту.')
        return True
    match = re.fullmatch(r'/(invite|invites|members|revokeinvite|blockuser|unblockuser)(?:@\w+)?(?:\s+(.*))?', text)
    if text != '👥 Учасники' and not match:
        return False
    uid = update.effective_user.id
    try:
        access.require_admin(uid)
        if not match:
            await update.message.reply_text(HELP)
            return True
        command, arg = match.groups()
        if command == 'invite':
            if arg:
                raise ValueError('Надішли /invite без аргументів.')
            # Resolve username before creating an invitation, so network failure
            # cannot leave an unreachable secret in the database.
            bot = await context.bot.get_me()
            identifier, token = access.create_invite(uid)
            try:
                await update.message.reply_text(f'Запрошення №{identifier} · одноразове · 7 днів\nhttps://t.me/{bot.username}?start=invite_{token}\nСкасувати: /revokeinvite {identifier}\nНадішли посилання потрібній людині. ШІ їй не надається.')
            except Exception:
                # Even an uncertain delivery must not leave an unmanaged live link.
                access.revoke_invite(uid,identifier)
                raise
        elif command == 'invites':
            rows = access.list_invites(uid)
            message = ('Активні невикористані запрошення (до 100 останніх):\n' +
                '\n'.join(f"№{row['id']} — до {row['expires_at'][:19]} UTC" for row in rows) +
                '\nСкасувати: /revokeinvite номер') if rows else 'Активних невикористаних запрошень немає. /invite'
            await send_chunks(update.message,message)
        elif command == 'members':
            rows = access.list_members(uid)
            await send_chunks(update.message,'👥 Учасники\n'+'\n'.join(f'{row["user_id"]} — '+('активний' if row['active'] else 'доступ призупинено') for row in rows) if rows else 'Запрошених учасників ще немає. /invite')
        else:
            if not arg or not arg.isdecimal():
                raise ValueError('Потрібен додатний цілий номер.\n'+HELP)
            identifier = int(arg)
            if not 1 <= identifier <= 9223372036854775807:
                raise ValueError('Номер має бути від 1 до 9223372036854775807. Перевір ID через /members або /invites.')
            if command == 'revokeinvite':
                changed = access.revoke_invite(uid,identifier)
                await update.message.reply_text('Запрошення скасовано.' if changed else 'Активного невикористаного запрошення з таким номером немає.')
            else:
                access.set_active(uid,identifier,command == 'unblockuser')
                await update.message.reply_text('Доступ повернуто.' if command == 'unblockuser' else 'Доступ призупинено. Особисті записи збережено.')
    except ValueError as error:
        await update.message.reply_text(str(error))
    return True
