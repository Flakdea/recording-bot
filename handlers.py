from datetime import datetime

from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

import keyboards as kb
from states import BookingStates

import aiosqlite
from config import DB_NAME
import config
import logging

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    #"""Стартовая команда: приветствие и вывод категорий."""
    await state.clear()  # Очищаем старые состояния, если они были
    reply_markup = await kb.get_categories_keyboard()

    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        "Добро пожаловать в нашу студию красоты.\n\n"
        "Пожалуйста, выберите интересующую вас категорию услуг:",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.choosing_category)


@router.callback_query(F.data.startswith("cat_"), BookingStates.choosing_category)
async def process_category_choice(callback: types.CallbackQuery, state: FSMContext):
    #"""Обработка выбора категории ➔ Показ списка услуг."""
    category_name = callback.data.split("_")[1]

    # Сохраняем выбранную категорию в контекст FSM
    await state.update_data(chosen_category=category_name)

    reply_markup = await kb.get_services_keyboard(category_name)

    await callback.message.edit_text(
        f"Вы выбрали категорию: *{category_name}*\n"
        "Теперь выберите конкретную услугу для записи:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.choosing_service)


# ИСПРАВЛЕНО: убрали фильтр состояния, теперь кнопка сработает из любого места
@router.callback_query(F.data == "back_to_categories")
async def process_back_to_categories(callback: types.CallbackQuery, state: FSMContext):
    """Возврат назад к категориям из любого состояния или после завершения записи."""
    await state.clear() # На всякий случай очищаем состояние
    reply_markup = await kb.get_categories_keyboard()
    await callback.message.edit_text(
        "📱 Главное меню\n\nПожалуйста, выберите интересующую вас категорию услуг:",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.choosing_category)


@router.callback_query(F.data.startswith("srv_"), BookingStates.choosing_service)
async def process_service_choice(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора конкретной услуги ➔ Показ интерактивного календаря с защитой."""
    service_id = int(callback.data.split("_")[1])  # Проверьте, чтобы тут было split("_")[1]
    await state.update_data(chosen_service_id=service_id)

    # Теперь здесь будут чистые строки дат
    available_dates = await kb.get_available_dates_for_service(service_id)

    if not available_dates:
        await callback.answer(
            "⚠️ К сожалению, на эту услугу сейчас нет доступных мастеров или свободных окон.\n"
            "Пожалуйста, выберите другую процедуру.",
            show_alert=True
        )
        return

    reply_markup = await kb.get_calendar_keyboard(service_id=service_id)

    await callback.message.edit_text(
        "📅 <b>Выберите подходящую дату для записи:</b>\n\n"
        "Доступные для записи дни подсвечены числами. "
        "Точки (·) означают, что свободных мастеров на этот день нет.",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.choosing_date)


@router.callback_query(F.data.startswith("cal_"), BookingStates.choosing_date)
async def process_calendar_navigation(callback: types.CallbackQuery, state: FSMContext):
    """Перелистывание месяцев в календаре."""
    _, year, month = callback.data.split("_")
    data = await state.get_data()
    service_id = data.get("chosen_service_id")

    reply_markup = await kb.get_calendar_keyboard(
        service_id=service_id,
        year=int(year),
        month=int(month)
    )

    await callback.message.edit_reply_markup(reply_markup=reply_markup)
    await callback.answer()


@router.callback_query(F.data == "back_to_services", BookingStates.choosing_date)
async def process_back_to_services(callback: types.CallbackQuery, state: FSMContext):
    """Кнопка возврата из календаря назад к списку услуг."""
    data = await state.get_data()
    category_name = data.get("chosen_category")

    reply_markup = await kb.get_services_keyboard(category_name)
    await callback.message.edit_text(
        f"Вы выбрали категорию: *{category_name}*\n"
        "Выберите услугу:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.choosing_service)


@router.callback_query(F.data == "ignore")
async def process_ignore(callback: types.CallbackQuery):
    """Игнорируем нажатия на пустые ячейки календаря и дни недели."""
    await callback.answer()





# 1. Исправленный чистый хэндлер выбора даты (без отладки)
@router.callback_query(F.data.startswith("date_"), BookingStates.choosing_date)
async def process_date_choice(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_")[1]
    await state.update_data(chosen_date=date_str)

    data = await state.get_data()
    service_id = data.get("chosen_service_id")

    reply_markup = await kb.get_masters_for_date_keyboard(service_id, date_str)
    formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")

    await callback.message.edit_text(
        f"📅 Выбранная дата: *{formatted_date}*\n\n"
        "👥 Выберите свободного мастера на этот день:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.choosing_master)

@router.callback_query(F.data == "back_to_calendar", BookingStates.choosing_master)
async def process_back_to_calendar(callback: types.CallbackQuery, state: FSMContext):
    """Возврат назад к календарю выбора дат."""
    data = await state.get_data()
    service_id = data.get("chosen_service_id")

    reply_markup = await kb.get_calendar_keyboard(service_id=service_id)
    await callback.message.edit_text(
        "📅 *Выберите подходящую дату для записи:*\n\n"
        "Доступные для записи дни подсвечены числами.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.choosing_date)


# 2. Хэндлер выбора мастера ➔ Показ доступного времени
@router.callback_query(F.data.startswith("master_"), BookingStates.choosing_master)
async def process_master_choice(callback: types.CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_")[1])
    await state.update_data(chosen_master_id=master_id)

    data = await state.get_data()
    service_id = data.get("chosen_service_id")
    date_str = data.get("chosen_date")

    # Получаем клавиатуру времени и флаг наличия окон
    reply_markup, has_slots = await kb.get_time_slots_keyboard(master_id, date_str, service_id)

    if not has_slots:
        await callback.answer("⚠️ К сожалению, у этого мастера нет окон на полную длительность услуги!",
                              show_alert=True)
        return

    await callback.message.edit_text(
        "🕒 *Выберите удобное время для записи:*\n\n",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.choosing_time)


# 3. Кнопка возврата назад к списку мастеров
@router.callback_query(F.data == "back_to_masters", BookingStates.choosing_time)
async def process_back_to_masters(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    service_id = data.get("chosen_service_id")
    date_str = data.get("chosen_date")

    reply_markup = await kb.get_masters_for_date_keyboard(service_id, date_str)
    await callback.message.edit_text(
        "👥 Выберите свободного мастера на этот день:",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.choosing_master)


@router.callback_query(F.data.startswith("time_"), BookingStates.choosing_time)
async def process_time_choice(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора времени ➔ Вывод финального чека для проверки (HTML + красивое время)."""
    # Извлекаем выбранное время начала (например, "10:30")
    _, _, start_time = callback.data.split("_")
    await state.update_data(chosen_time_start=start_time)

    data = await state.get_data()

    # Собираем текстовые названия для чека из базы данных
    async with aiosqlite.connect(DB_NAME) as db:
        # Получаем данные услуги
        async with db.execute(
                "SELECT service, price, time FROM Services WHERE id = ?",
                (data.get("chosen_service_id"),)
        ) as c:
            service_name, price, duration = await c.fetchone()

        # Получаем имя мастера
        async with db.execute(
                "SELECT name FROM Masters WHERE id = ?",
                (data.get("chosen_master_id"),)
        ) as c:
            row_master = await c.fetchone()
            master_name = row_master[0] if row_master else "Неизвестный мастер"

    formatted_date = datetime.strptime(data.get("chosen_date"), "%Y-%m-%d").strftime("%d.%m.%Y")

    # Используем созданную функцию форматирования времени
    pretty_duration = format_duration(duration)

    # Формируем красивый текст чека на HTML (для единообразия)
    summary_text = (
        "📋 <b>Проверьте детали вашей записи:</b>\n\n"
        f"💅 <b>Услуга:</b> {service_name}\n"
        f"💰 <b>Стоимость:</b> {price} RSD\n"
        f"⏳ <b>Длительность:</b> {pretty_duration}\n"
        f"👥 <b>Мастер:</b> {master_name}\n"
        f"📅 <b>Дата:</b> {formatted_date}\n"
        f"🕒 <b>Время начала:</b> {start_time}\n\n"
        "Если всё верно, нажмите кнопку ниже для подтверждения визита."
    )

    await callback.message.edit_text(
        summary_text,
        parse_mode="HTML",
        reply_markup=kb.get_confirm_keyboard()
    )
    # Переводим в состояние ожидания клика по чеку
    await state.set_state(None)


def format_duration(minutes: int) -> str:
    """Форматирует минуты в красивую строку (например: 90 -> '1 ч. 30 мин.', 25 -> '25 мин.')"""
    if minutes < 60:
        return f"{minutes} мин."

    hours = minutes // 60
    rem_minutes = minutes % 60

    if rem_minutes == 0:
        return f"{hours} ч."
    return f"{hours} ч. {rem_minutes} мин."


@router.callback_query(F.data == "confirm_booking")
async def process_confirm_booking(callback: types.CallbackQuery, state: FSMContext):
    """Действие при успешном подтверждении записи с защитой от спецсимволов в HTML и красивым временем."""
    data = await state.get_data()

    success = await kb.book_time_slots(
        master_id=data.get("chosen_master_id"),
        date_str=data.get("chosen_date"),
        start_time=data.get("chosen_time_start"),
        service_id=data.get("chosen_service_id")
    )

    if success:
        # 1. Получаем текстовые данные для отправки админу
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT service, price, time FROM Services WHERE id = ?",
                                  (data.get("chosen_service_id"),)) as c:
                service_name, price, duration = await c.fetchone()
            async with db.execute("SELECT name FROM Masters WHERE id = ?", (data.get("chosen_master_id"),)) as c:
                row_master = await c.fetchone()
                master_name = row_master[0] if row_master else "Неизвестный мастер"
            await db.execute("""
                                    INSERT INTO Bookings (user_id, service_id, master_id, date, time_start, created_at)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (
                callback.from_user.id,
                data.get("chosen_service_id"),
                data.get("chosen_master_id"),
                data.get("chosen_date"),
                data.get("chosen_time_start"),
                str(datetime.now())
            ))
            await db.commit()


        formatted_date = datetime.strptime(data.get("chosen_date"), "%Y-%m-%d").strftime("%d.%m.%Y")

        # Экранируем имена клиентов, чтобы HTML разметка не ломалась от знаков < или >
        client_name = callback.from_user.full_name.replace("<", "&lt;").replace(">", "&gt;")

        if callback.from_user.username:
            client_username = f"@{callback.from_user.username}".replace("<", "&lt;").replace(">", "&gt;")
        else:
            client_username = "нет юзернейма"

        # Форматируем длительность с помощью нашей новой функции
        pretty_duration = format_duration(duration)

        # 2. Текст чека для администратора студии (ПЕРЕВЕДЕН НА HTML С СЕФЬТИ-ПРАВИЛАМИ)
        admin_notification = (
            "🔔 <b>Новая запись на процедуру!</b>\n\n"
            f"👤 <b>Клиент:</b> {client_name} ({client_username})\n"
            f"💅 <b>Услуга:</b> {service_name}\n"
            f"💰 <b>Стоимость:</b> {price} RSD\n"
            f"⏳ <b>Длительность:</b> {pretty_duration}\n"
            f"👥 <b>Мастер:</b> {master_name}\n"
            f"📅 <b>Дата:</b> {formatted_date}\n"
            f"🕒 <b>Время начала:</b> {data.get('chosen_time_start')}\n"
        )
        # Отправляем чек по ID администратора
        if config.ADMIN_ID:
            try:
                await callback.bot.send_message(chat_id=config.ADMIN_ID, text=admin_notification, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление админу: {e}")

        # 3. Ответ самому клиенту (также обновляем вывод времени для клиента)
        await callback.message.edit_text(
            f"🎉 <b>Вы успешно записаны!</b>\n\n"
            f"Ждем вас на процедуру «{service_name}» ({pretty_duration}) "
            f"к мастеру {master_name} — {formatted_date} в {data.get('chosen_time_start')}.\n\n"
            "Спасибо, что выбрали нашу студию! ✨",
            parse_mode="HTML",
            reply_markup=kb.get_main_menu_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка при бронировании.</b>\n"
            "Пожалуйста, попробуйте выбрать другое время или начните сначала.",
            parse_mode="HTML",
            reply_markup=kb.get_main_menu_keyboard()
        )

    await state.clear()

@router.callback_query(F.data == "cancel_booking")
async def process_cancel_booking(callback: types.CallbackQuery, state: FSMContext):
    """Сброс записи и возврат в начало."""
    await state.clear()
    reply_markup = await kb.get_categories_keyboard()
    await callback.message.edit_text(
        "Запись отменена.\n\nПожалуйста, выберите интересующую вас категорию услуг заново:",
        reply_markup=reply_markup
    )
    await state.set_state(BookingStates.choosing_category)



from aiogram.filters import Command

@router.message(Command("my_bookings"))
async def cmd_my_bookings(message: types.Message):
    """Вывод актуальных записей пользователя."""
    user_id = message.from_user.id
    today_str = str(datetime.now().date())

    sql = """
        SELECT B.date, B.time_start, S.service, S.price, M.name
        FROM Bookings B
        JOIN Services S ON B.service_id = S.id
        JOIN Masters M ON B.master_id = M.id
        WHERE B.user_id = ? AND B.date >= ?
        ORDER BY B.date ASC, B.time_start ASC
    """

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(sql, (user_id, today_str)) as cursor:
            bookings = await cursor.fetchall()

    if not bookings:
        await message.answer(
            "📋 <b>У вас пока нет активных записей.</b>\n\n"
            "Чтобы записаться на процедуру, введите команду /start",
            parse_mode="HTML"
        )
        return

    response_text = "📋 <b>Ваши актуальные записи:</b>\n\n"

    for row in bookings:
        date_raw, time_start, service, price, master = row
        formatted_date = datetime.strptime(date_raw, "%Y-%m-%d").strftime("%d.%m.%Y")

        response_text += (
            f"📅 <b>Дата:</b> {formatted_date}\n"
            f"🕒 <b>Время:</b> {time_start}\n"
            f"💅 <b>Процедура:</b> {service}\n"
            f"👥 <b>Мастер:</b> {master}\n"
            f"💰 <b>Стоимость:</b> {price} RSD\n"
            f"───────────────────\n\n"
        )

    await message.answer(response_text, parse_mode="HTML")
