"""Validated actual sets and optional verbatim notes, independent of AI."""
import re


def note_text(value):
    if not isinstance(value, str) or len(value) > 1000:
        raise ValueError('Нотатка — текст до 1000 символів.')
    if any(ord(char) < 32 and char not in '\n\t\r' for char in value):
        raise ValueError('Нотатка містить непідтримувані службові символи.')
    return value


def parse_sets(text):
    lines = text.strip().splitlines()
    if not 1 <= len(lines) <= 100:
        raise ValueError('Введи 1–100 підходів, кожен окремим рядком: кг повторення; нотатка.')
    result = []
    for line in lines:
        values, separator, note = line.partition(';')
        match = re.fullmatch(r'\s*(\d+(?:[.,]\d+)?)\s*(?:[xх×/]\s*|\s+)(\d+)\s*', values)
        if not match:
            raise ValueError('Кожен рядок: кг повторення; нотатка. Наприклад: 70x10; боліло коліно')
        weight, reps = float(match[1].replace(',', '.')), int(match[2])
        if not 0 <= weight <= 1000 or not 1 <= reps <= 1000:
            raise ValueError('Перевір значення: 0–1000 кг, 1–1000 повторень.')
        item = dict(weight=weight, reps=reps)
        if separator:
            item['note'] = note_text(note)
        result.append(item)
    return result


def record_id(value):
    """Validate externally supplied record identifiers before SQLite binding."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError('Номер запису має бути додатним цілим числом.')
    text = str(value)
    if not text.isdecimal() or len(text) > 19:
        raise ValueError('Номер запису має бути від 1 до 9223372036854775807.')
    number = int(text)
    if not 1 <= number <= 9223372036854775807:
        raise ValueError('Номер запису має бути від 1 до 9223372036854775807.')
    return number
