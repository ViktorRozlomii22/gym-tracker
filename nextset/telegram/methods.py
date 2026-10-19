"""Reviewed method cards, browsed one at a time without model inference."""
from telegram import ReplyKeyboardMarkup
from nextset.knowledge.catalog import references, model_reference

GROUPS={'muscle':'💪 Ріст м’язів','strength':'🏋️ Сила','balanced':'⚖️ Сила й м’язи'}

def render(key):
    card=references()[key]
    lines=[card['title'],'🎯 Фокус: '+card['focus'],'👤 Кому підходить: '+card['suited_for'],
        '\n➕ Плюси',*('• '+x for x in card['pros']),
        '\n➖ Мінуси',*('• '+x for x in card['cons']),
        '\n🗓 3 рази на тиждень: '+card['three_day_fit'],
        '📈 Як прогресувати: '+card['progression'],
        '\nМежі: '+card['limitations'],card['evidence_note'],
        'Джерела: '+ ' | '.join(card['sources'])]
    return '\n'.join(lines)

async def menu(update,context,category=None):
    catalog=references()
    if category not in GROUPS:
        keyboard=[[v] for v in GROUPS.values()]+[['🔙 Головне меню']]
        text=f'🧭 Методи тренування · {len(catalog)} варіантів\nОбери мету, потім відкрий картку. Чотири роки стажу самі по собі не визначають найкращий метод.'
    else:
        keys=[key for key,value in catalog.items() if value['category']==category]
        keyboard=[['📖 '+catalog[key]['title']] for key in keys]+[['🧭 Усі методи','🔙 Головне меню']]
        text=GROUPS[category]+'\nОбери один варіант, щоб побачити фокус, плюси й мінуси. Перегляд не змінює твій поточний план.'
    await update.message.reply_text(text,reply_markup=ReplyKeyboardMarkup(keyboard,resize_keyboard=True))

async def show(update,context,key):
    if key not in references():
        raise ValueError('Невідомий метод. Відкрий /programs.')
    context.user_data['method_preview']=key
    await update.message.reply_text(render(key),reply_markup=ReplyKeyboardMarkup(
        [['✅ Обрати цей метод'],['🧭 Усі методи','🔙 Головне меню']],resize_keyboard=True))

async def route(update,context):
    text=update.message.text.strip()
    if text in ('🧭 Усі методи','🧭 Програми','/methods'):
        await menu(update,context);return True
    for key,label in GROUPS.items():
        if text==label:
            await menu(update,context,key);return True
    if text.startswith('/method '):
        await show(update,context,text.split(maxsplit=1)[1].strip());return True
    for key,card in references().items():
        if text=='📖 '+card['title']:
            await show(update,context,key);return True
    if text=='✅ Обрати цей метод':
        key=context.user_data.get('method_preview')
        if key not in references():
            await menu(update,context);return True
        await update.message.reply_text('Змінити метод на «'+references()[key]['title']+'»? Поточний блок буде перенесено в історію, чернетку скинуто. Записи тренувань і PR залишаться.',
            reply_markup=ReplyKeyboardMarkup([['🔄 Підтвердити зміну методу'],['🧭 Усі методи']],resize_keyboard=True))
        return True
    if text=='🔄 Підтвердити зміну методу':
        key=context.user_data.pop('method_preview',None)
        if key not in references():
            await menu(update,context);return True
        import nextset.coaching.programs as programs
        await programs.handle(update,context,'/program',key)
        from nextset.telegram.ui import setup
        await setup(update,context)
        return True
    return False
