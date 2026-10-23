"""Public Telegram command menu, separate from startup and routing behavior."""
BOT_COMMANDS=(
    ('start','Головне меню'),
    ('help','Як користуватися щоденником'),
    ('programs','Методи: фокус, плюси й мінуси'),
    ('profile','Мій профіль'),
    ('plan','Наступна сесія'),
    ('block','Графік на 8 тижнів'),
    ('checkin','Самопочуття перед тренуванням'),
    ('history','Історія тренувань і підходів'),
    ('exercise','Історія однієї вправи'),
    ('graph','Графік за 7, 30, 56, 90 або 365 днів'),
    ('measure','Записати виміри тіла'),
    ('remind','Налаштувати нагадування'),
    ('status','Самопочуття або хвороба'),
    ('extra','Легкий четвертий день'),
    ('feedback','RIR, біль та складність вправи'),
    ('swap','Замінити вправу в плані'),
    ('weekly','Звіт за останні 7 днів'),
    ('weeklyai','Висновки за тиждень з джерелами'),
    ('ask','Питання до наукової бази'),
    ('sources','Джерела локальної бази'),
    ('aistatus','Перевірити стан ШІ'),
    ('airesult','Останній результат ШІ'),
    ('aicancel','Скасувати запит ШІ'),
    ('ai','Розібрати запис локальним ШІ'),
    ('backup','Локальна резервна копія'),
    ('coachhelp','Усі команди налаштування плану'),
    ('cancel','Скасувати введення'),
)

MEMBER_COMMANDS=tuple(item for item in BOT_COMMANDS if item[0] in {
    'start','help','history','exercise','graph','measure','remind','weekly','cancel'}) + (
    ('account','Мій доступ і Telegram ID'),('note','Нотатка до вправи'),
    ('setnote','Нотатка до підходу'),('trainingnote','Нотатка до тренування'))
ADMIN_COMMANDS=BOT_COMMANDS + (
    ('invite','Створити одноразове запрошення'),('members','Учасники бота'),
    ('revokeinvite','Скасувати запрошення'),('blockuser','Призупинити доступ'),
    ('unblockuser','Повернути доступ'),('account','Мій доступ і Telegram ID'))
