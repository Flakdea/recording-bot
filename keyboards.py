import aiosqlite
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from config import DB_NAME


async def get_categories_keyboard() -> InlineKeyboardMarkup:
    #"""Извлекает уникальные категории из БД и строит клавиатуру."""
    builder = InlineKeyboardBuilder()

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT DISTINCT category FROM Services") as cursor:
            async for row in cursor:
                category_name = row[0]
                # Префикс 'cat_' поможет хэндлеру понять, что выбрана категория
                builder.button(text=category_name, callback_data=f"cat_{category_name}")

    builder.adjust(1)  # Кнопки в один ряд друг под другом
    return builder.as_markup()


import re


async def get_services_keyboard(category_name: str) -> InlineKeyboardMarkup:
    """Извлекает уникальные услуги БЕЗ цен, полностью исключая дубли из-за дефисов и пробелов."""
    builder = InlineKeyboardBuilder()
    seen_services = set()

    async with aiosqlite.connect(DB_NAME) as db:
        sql = "SELECT id, service FROM Services WHERE category = ? ORDER BY price ASC"
        async with db.execute(sql, (category_name,)) as cursor:
            async for row in cursor:
                service_id, name = row

                # 1. Базовая очистка от цифр и скобок
                clean_name = re.sub(r'^\d+\.\s*', '', name)
                clean_name = re.sub(r'\(.*?\)', '', clean_name)

                # 2. Сокращения
                clean_name = re.sub(r'без покрытия', 'без покр.', clean_name, flags=re.IGNORECASE)
                clean_name = re.sub(r'с покрытием', 'с покр.', clean_name, flags=re.IGNORECASE)
                clean_name = re.sub(r'комбинированный', 'комбин.', clean_name, flags=re.IGNORECASE)
                clean_name = re.sub(r'аппаратный', 'аппар.', clean_name, flags=re.IGNORECASE)

                clean_name = re.sub(r'\s+', ' ', clean_name).strip()
                clean_name = clean_name.capitalize()

                # 3. УМНЫЙ СРАВНИВАТЕЛЬ ДУБЛИКАТОВ
                # Создаем "скелет" строки: переводим в нижний регистр, убираем дефисы и пробелы
                # "Маникюр гель-лак" и "Маникюр гель лак" превратятся в одинаковый "маникюргеллак"
                match_skeleton = clean_name.lower().replace("-", "").replace(" ", "")

                if match_skeleton in seen_services:
                    continue

                seen_services.add(match_skeleton)
                builder.button(text=clean_name, callback_data=f"srv_{service_id}")

    builder.button(text="⬅️ Назад к категориям", callback_data="back_to_categories")
    builder.adjust(1)
    return builder.as_markup()


import calendar
from datetime import datetime

async def get_available_dates_for_service(service_id: int) -> set:
    """Получает сетку дат (YYYY-MM-DD), в которые работают мастера для этой услуги."""
    dates = set()
    async with aiosqlite.connect(DB_NAME) as db:
        sql = """
            SELECT DISTINCT MSch.date 
            FROM Master_Schedule MSch
            JOIN Master_Services MSrv ON MSch.master_id = MSrv.master_id
            WHERE MSrv.service_id = ?
        """
        async with db.execute(sql, (service_id,)) as cursor:
            async for row in cursor:
                # ИСПРАВЛЕНО: Извлекаем строку даты из кортежа row
                dates.add(row[0])
    return dates



async def get_calendar_keyboard(service_id: int, year: int = None, month: int = None) -> InlineKeyboardMarkup:
    """Генерирует интерактивный календарь с корректной сеткой 7x7."""
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    # Получаем доступные даты для этой услуги из базы
    available_dates = await get_available_dates_for_service(service_id)

    builder = InlineKeyboardBuilder()

    # Массив для хранения схемы размещения кнопок (сколько кнопок в каждой строке)
    adjust_schema = []

    # 1. Шапка: Название месяца и год (1 кнопка на всю строку)
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    builder.button(text=f"{month_names[month - 1]} {year}", callback_data="ignore")
    adjust_schema.append(1)

    # 2. Строка дней недели (7 кнопок в строке)
    for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
        builder.button(text=day, callback_data="ignore")
    adjust_schema.append(7)

    # 3. Календарная сетка чисел
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        for day in week:
            if day == 0:
                # Пустая ячейка для выравнивания
                builder.button(text=" ", callback_data="ignore")
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"

                # Проверяем доступность даты
                is_available = date_str in available_dates
                is_past = datetime.strptime(date_str, "%Y-%m-%d").date() < now.date()

                if is_available and not is_past:
                    builder.button(text=str(day), callback_data=f"date_{date_str}")
                else:
                    builder.button(text="·", callback_data="ignore")

        # Каждая неделя — это строго 7 кнопок в строке
        adjust_schema.append(7)

    # 4. Навигация по месяцам (Назад / Вперед)
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    # Кнопки управления (2 кнопки в ряд)
    if datetime(year, month, 1) > datetime(now.year, now.month, 1):
        builder.button(text="⬅️ Пред. месяц", callback_data=f"cal_{prev_year}_{prev_month}")
    else:
        builder.button(text=" ", callback_data="ignore")

    builder.button(text="➡️ След. месяц", callback_data=f"cal_{next_year}_{next_month}")
    adjust_schema.append(2)

    # 5. Кнопка возврата назад (1 кнопка на всю строку)
    builder.button(text="⬅️ Назад к услугам", callback_data="back_to_services")
    adjust_schema.append(1)

    # Применяем точную схему выравнивания рядов
    builder.adjust(*adjust_schema)

    return builder.as_markup()




async def get_masters_for_date_keyboard(service_id: int, date_str: str) -> InlineKeyboardMarkup:
    """Генерирует список мастеров, доступных для выбранной услуги в указанную дату."""
    builder = InlineKeyboardBuilder()

    async with aiosqlite.connect(DB_NAME) as db:
        sql = """
            SELECT M.id, M.name, M.post
            FROM Masters M
            JOIN Master_Schedule MSch ON M.id = MSch.master_id
            JOIN Master_Services MSrv ON M.id = MSrv.master_id
            WHERE MSrv.service_id = ? AND MSch.date = ?
        """
        async with db.execute(sql, (service_id, date_str)) as cursor:
            async for row in cursor:
                master_id, name, post = row
                # Текст кнопки: "Ирина (Топ-мастер)"
                button_text = f"{name} ({post})" if post else name
                builder.button(text=button_text, callback_data=f"master_{master_id}")

    builder.button(text="⬅️ Назад к календарю", callback_data="back_to_calendar")
    builder.adjust(1)
    return builder.as_markup()


import math


async def get_time_slots_keyboard(master_id: int, date_str: str, service_id: int) -> tuple[InlineKeyboardMarkup, bool]:
    """
    Ищет доступные цепочки временных слотов с шагом 10 минут.
    Исправлено: извлечение числа из кортежа SQLite row[0].
    """
    builder = InlineKeyboardBuilder()

    async with aiosqlite.connect(DB_NAME) as db:
        # 1. Получаем длительность выбранной услуги в минутах
        async with db.execute("SELECT time FROM Services WHERE id = ?", (service_id,)) as cursor:
            row = await cursor.fetchone()
            # ИСПРАВЛЕНО: берем первый элемент кортежа row[0]
            service_duration = row[0] if row else 60

        # Округляем длительность до ближайшего числа, кратного 10 в большую сторону
        rounded_duration = math.ceil(service_duration / 10) * 10
        slots_needed = rounded_duration // 10

        sql = """
            SELECT TS.id, TS.time_start, TS.is_booked
            FROM Time_Slots TS
            JOIN Master_Schedule MSch ON TS.schedule_id = MSch.id
            WHERE MSch.master_id = ? AND MSch.date = ?
            ORDER BY TS.time_start ASC
        """
        async with db.execute(sql, (master_id, date_str)) as cursor:
            slots = await cursor.fetchall()

    has_slots = False
    for i in range(len(slots) - slots_needed + 1):
        chain_available = True
        for j in range(slots_needed):
            # slots[i + j][2] - это поле is_booked в кортеже слота
            if slots[i + j][2] == 1:
                chain_available = False
                break

        if chain_available:
            time_start = slots[i][1]  # Извлекаем строку времени
            slot_id = slots[i][0]  # Извлекаем ЧИСЛОВОЙ ID слота

            builder.button(text=time_start, callback_data=f"time_{slot_id}_{time_start}")
            has_slots = True

    builder.button(text="⬅️ Назад к мастерам", callback_data="back_to_masters")
    builder.adjust(5)

    return builder.as_markup(), has_slots


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения записи."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить запись", callback_data="confirm_booking")
    builder.button(text="❌ Отменить и начать заново", callback_data="cancel_booking")
    builder.adjust(1)
    return builder.as_markup()

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📱 В главное меню", callback_data="back_to_categories")
    return builder.as_markup()


async def book_time_slots(master_id: int, date_str: str, start_time: str, service_id: int) -> bool:
    """Бронирует цепочку 10-минутных слотов в БД с учетом округления. Исправлено row[0]."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT time FROM Services WHERE id = ?", (service_id,)) as cursor:
            row = await cursor.fetchone()
            # ИСПРАВЛЕНО: берем первый элемент кортежа row[0]
            duration = row[0] if row else 60

        rounded_duration = math.ceil(duration / 10) * 10
        slots_needed = rounded_duration // 10

        sql = """
            SELECT TS.id, TS.time_start
            FROM Time_Slots TS
            JOIN Master_Schedule MSch ON TS.schedule_id = MSch.id
            WHERE MSch.master_id = ? AND MSch.date = ?
            ORDER BY TS.time_start ASC
        """
        async with db.execute(sql, (master_id, date_str)) as cursor:
            slots = await cursor.fetchall()

        start_index = None
        for idx, slot in enumerate(slots):
            # slot[1] — это строка времени (например, '10:00') в кортеже
            if slot[1] == start_time:
                start_index = idx
                break

        if start_index is None:
            return False

        # Собираем ID слотов (slot[0] — это ID в кортеже)
        ids_to_book = [slots[start_index + j][0] for j in range(slots_needed)]

        format_strings = ', '.join(['?'] * len(ids_to_book))
        await db.execute(
            f"UPDATE Time_Slots SET is_booked = 1 WHERE id IN ({format_strings})",
            ids_to_book
        )
        await db.commit()
        return True

