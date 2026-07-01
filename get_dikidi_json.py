import asyncio
import json
from playwright.async_api import async_playwright


async def get_json():
    # Наш секретный URL для получения услуг
    url = "https://dikidi.ru/mobile/ajax/newrecord/company_services/?lang=ru&array=1&company=1034930&master=&share="

    async with async_playwright() as p:
        # headless=True, чтобы не открывать лишних окон
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(" Подключаюсь к API Dikidi через браузер...")
        await page.goto(url)
        await page.wait_for_load_state("networkidle")

        # Прокрутка для подгрузки динамического контента
        for _ in range(3):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)

        # Забираем чистый текст, который выдал сервер (это и есть JSON)
        raw_text = await page.locator("body").inner_text()

        await browser.close()

        try:
            # Проверяем, что нам вернулся именно JSON, а не ошибка 503
            json_data = json.loads(raw_text)
            print(" JSON успешно получен!")

            # Сохраняем в файл
            with open("raw_services.json", "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            print(" Файл raw_services.json готов!")

        except json.JSONDecodeError:
            print(" Ошибка: Вместо данных пришел HTML-текст защиты.")
            print("Ответ сервера:", raw_text[:200])


asyncio.run(get_json())