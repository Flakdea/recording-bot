import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from json_to_db import build_schedule_job
from handlers import router as booking_router  # Импортируем наш роутер

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Регистрируем роутер в диспетчере
dp.include_router(booking_router)

async def main():

    scheduler = AsyncIOScheduler()
    scheduler.add_job(build_schedule_job, CronTrigger(hour=0, minute=0))
    scheduler.start()

    build_schedule_job()

    print(" Бот запускается...")
    try:
        # Настройка кнопки "Меню" в Telegram
        await bot.set_my_commands([
            types.BotCommand(command="start", description="Записаться на процедуру"),
            types.BotCommand(command="my_bookings", description="Мои активные записи")
        ])
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
