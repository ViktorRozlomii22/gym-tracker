"""Read-only plan views. Presentation never estimates or transfers training loads."""
from datetime import date

from nextset.core.exercises import NAMES
from nextset.visuals.calendar import calendar_rows


def span(value):
    if not isinstance(value, (list, tuple)):
        return str(value)
    return str(value[0]) if value[0] == value[1] else f'{value[0]}–{value[1]}'


def session_items(block, state, offset, today=None):
    """Use kg only from today's matching main-session prescription."""
    today = today or date.today()
    pending = state.get('pending') or {}
    cursor = block.get('start_cursor', 0) + offset
    matched = (block.get('approved') and block.get('created')
               and pending.get('block_id') == block['created']
               and pending.get('cursor') == cursor
               and state.get('cursor') == cursor
               and pending.get('day') == today.isoformat()
               and not pending.get('bonus'))
    if matched:
        return [dict(item, exercise=item['key']) for item in pending['items']]
    index = offset % 3
    overrides = block.get('overrides', {}).get(str(index), {})
    return [dict(item, exercise=overrides.get(item['exercise'], item['exercise']), weight=None)
            for item in block['sessions'][index]['items']]


def overview(block, state, today=None):
    """Small messages instead of a calendar image or one overwhelming wall."""
    status = 'прийнято' if block.get('approved') else 'проєкт — підтвердь перед початком'
    yield f'План на {block["length"]} тижнів · {status}\n3 тренування на тиждень: A → B → C.\nПідходи × повторення. Запас — скільки повторень залишити до відмови.'
    current = max(0, state.get('cursor', 0) - block.get('start_cursor', 0))
    week = min(current // 3, block['length'] - 1)
    for index, session in enumerate(block['sessions']):
        lines = [f'{chr(65 + index)}. {session["title"]} · тиждень {week + 1}']
        for item in session_items(block, state, week * 3 + index, today):
            kg = f'{item["weight"]:g} кг' if item.get('weight') is not None else 'кг: ще не розраховано'
            lines.append(f'• {NAMES[item["exercise"]]} — {span(item["sets"])} × {span(item["reps"])}; {kg}; запас {span(item["rir"])}')
        yield '\n'.join(lines)
    yield ('Відкрий «Наступна сесія», щоб отримати робочі кг за твоїми даними та самопочуттям. '
           'Розраховану сесію потрібно підтвердити перед тренуванням. '
           'Вага для майбутніх сесій не прогнозується. Повний розклад і рекомендації за тижнями — у «План Excel» або «Деталі плану».')


def schedule(block, state, today=None):
    for offset, slot in enumerate(calendar_rows(block, today)):
        yield slot, session_items(block, state, offset, today)
