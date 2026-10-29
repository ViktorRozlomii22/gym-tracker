"""Explicit note editing; notes are data, never coaching instructions."""
import re
import nextset.storage.database as db
from nextset.core.diary_entries import record_id

HELP = ('📝 Нотатки\nДо підходу під час запису: 70x10; боліло коліно\n'
        'До вже збереженого підходу: /setnote 12 2; текст\n'
        'До вправи: /note 12; текст\nДо тренування: /trainingnote 5; текст\n'
        '12 — номер запису вправи, 2 — номер підходу, 5 — номер тренування з /history.\n'
        'Та сама команда замінює нотатку. Щоб видалити — залиш текст після ; порожнім.')


async def clarify_pain(update, note):
    if re.search(r'бол[іи]|біль|боль|schmerz|pain', note, re.I):
        await update.message.reply_text('Ти описуєш поточний біль? Якщо так, повідом /status біль, щоб поставити план на паузу. Нотатка сама не встановлює діагноз і не змінює стан здоров’я.')


async def route(update, context):
    text = update.message.text
    if text == '📝 Нотатки':
        await update.message.reply_text(HELP)
        return True
    match = re.fullmatch(r'/(note|setnote|trainingnote)(?:@\w+)?(?:\s+(.*))?', text, re.S)
    if not match:
        return False
    command, args = match.groups()
    head, separator, note = (args or '').partition(';')
    try:
        ids = head.split()
        expected = 2 if command == 'setnote' else 1
        if not separator or len(ids) != expected or not all(x.isdecimal() for x in ids):
            raise ValueError(HELP)
        kind = {'note': 'exercise', 'setnote': 'set', 'trainingnote': 'training'}[command]
        db.update_diary_note(update.effective_user.id, kind, record_id(ids[0]), note,
                             int(ids[1]) if expected == 2 else None)
        await update.message.reply_text('✅ Нотатку збережено. /history' if note else 'Нотатку видалено. /history')
        await clarify_pain(update,note)
    except ValueError as error:
        await update.message.reply_text(str(error))
    return True
