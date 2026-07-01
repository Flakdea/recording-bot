import json
import sqlite3


# 1. Подключаемся к базе данных
db = sqlite3.connect('Salon.db')
cursor = db.cursor()

# Таблица 1: Мастера
cursor.execute('''CREATE TABLE IF NOT EXISTS Masters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    post TEXT
)''')

# Таблица 2: Услуги
cursor.execute('''CREATE TABLE IF NOT EXISTS Services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    service TEXT,
    price INTEGER,
    time INTEGER
)''')

# Таблица 3: Связующая таблица
cursor.execute('''CREATE TABLE IF NOT EXISTS Master_Services (
    master_id INTEGER,
    service_id INTEGER,
    PRIMARY KEY (master_id, service_id)
)''')
db.commit()

# Очищаем таблицу перед новой заливкой
cursor.execute('DElETE FROM Masters')
cursor.execute('DELETE FROM Services')
db.commit()

# СБРАСЫВАЕМ СЧЕТЧИК ID НА 0
cursor.execute("DELETE FROM sqlite_sequence WHERE name='Services'")
cursor.execute("DELETE FROM sqlite_sequence WHERE name='Masters'")
db.commit()

# 1. Добавляем мастеров
with open('masters.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

masters_dict = data.get("masters", {})

for master_info in masters_dict.values():
    name = master_info.get("username")
    post = master_info.get("post")

    if name: # Небольшая страховка, чтобы не записать пустую строку
        # ИСПРАВЛЕНО: добавили OR IGNORE для защиты от дубликатов UNIQUE
        cursor.execute('INSERT OR IGNORE INTO Masters (name, post) VALUES (?, ?)', (name, post))

db.commit()
print(" Успех! Все мастера и их должности перенесены в базу данных.")


# 2. Добавляем сервисы
with open('raw_services.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Достаем список категорий
categories = data.get('data', {}).get('list', [])

count = 0

#  Первый цикл: бежим по категориям
for category in categories:
    #  Достаем название текущей категории
    category_name = category.get('category_value')

    # Из этой же категории достаем список конкретных услуг
    services = category.get('services', [])

    # Второй цикл: бежим по конкретным услугам внутри этой категории
    for item in services:
        service_name = item.get('name')
        price = item.get('price')
        time = item.get('time')

        # Если нашли название услуги — сохраняем в базу
        if service_name:
            cursor.execute(
                'INSERT INTO Services (category, service, price, time) VALUES (?, ?, ?, ?)',
                (category_name, service_name, price, time)
            )
            count += 1

# Сохраняем
db.commit()
print(f" Успех! Перенесено {count} услуг. Категории распределены автоматически!")



# Объединяем в третью
def link_services_to_master(master_id, service_ids_list):
    for s_id in service_ids_list:
        # Проверяем, существует ли вообще такая услуга в базе, чтобы не создать битую связь
        cursor.execute('SELECT id FROM Services WHERE id = ?', (s_id,))
        if cursor.fetchone():
            # Записываем связь в таблицу Master_Services
            cursor.execute(
                'INSERT OR IGNORE INTO Master_Services (master_id, service_id) VALUES (?, ?)',
                (master_id, s_id)
            )
            print(f" Услуга с ID {s_id} успешно добавлена мастеру (ID: {master_id})")
        else:
            print(f" Услуга с ID {s_id} не найдена в таблице Services!")

    db.commit()
link_services_to_master(1,[9,70,71,72,73,74,75,76,78,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101])
link_services_to_master(2,[1,2,3,4,5,6,9,71,72,73,74,75,76,77,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101])
link_services_to_master(3,[102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127])
link_services_to_master(4,[7,8,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155])
link_services_to_master(5,[10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70])
link_services_to_master(6,[10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54])

def show_all_services():
    cursor.execute('SELECT * FROM Services')
    result = cursor.fetchall()
    for item in result:
        print(item)

def show_all_masters():
    cursor.execute('SELECT * FROM Masters')
    result = cursor.fetchall()
    for item in result:
        print(item)

def show_services_by_master(master_name):
    # Склеиваем три таблицы через JOIN по их ID связям
    cursor.execute('''
        SELECT Services.id, Services.category, Services.service, Services.price, Services.time
        FROM Services
        JOIN Master_Services ON Services.id = Master_Services.service_id
        JOIN Masters ON Masters.id = Master_Services.master_id
        WHERE Masters.name = ?
    ''', (master_name,))

    results = cursor.fetchall()
    print(f"\n---  Полный прайс-лист мастера {master_name} ---")
    if not results:
        print("У этого мастера пока нет привязанных услуг.")
        return

    for row in results:
        print(f"ID услуги: {row[0]} | Категория: {row[1]} | Название: {row[2]} | Цена: {row[3]} RSD | Время: {row[4]} мин.")


show_all_masters()
show_all_services()
show_services_by_master('Мари')




from datetime import datetime, timedelta

DB_NAME = "Salon.db"

def get_master_services(cursor, master_id):
    #"""Получает список ID услуг, которые оказывает мастер."""
    cursor.execute("SELECT service_id FROM Master_Services WHERE master_id = ?", (master_id,))
    return {row[0] for row in cursor.fetchall()}


def has_service_conflict(cursor, master_id, date):
    current_services = get_master_services(cursor, master_id)

    cursor.execute("SELECT master_id FROM Master_Schedule WHERE date = ?", (date,))
    working_masters = [row[0] for row in cursor.fetchall()]  # Извлечение id из кортежа

    for wm_id in working_masters:
        wm_services = get_master_services(cursor, wm_id)
        if current_services.intersection(wm_services):
            return True

    return False


def generate_10min_slots():
    """Генерирует интервалы с 10:00 до 21:00 с шагом в 10 минут."""
    slots = []
    start = datetime.strptime("10:00", "%H:%M")
    end = datetime.strptime("21:00", "%H:%M")
    while start < end:
        slots.append(start.strftime("%H:%M"))
        # Меняем шаг на 10 минут
        start += timedelta(minutes=10)
    return slots


import sqlite3
from datetime import datetime, timedelta
import math
from config import DB_NAME


# ... ваши функции get_master_services, has_service_conflict, generate_10min_slots ...

def build_schedule_job():
    """Эта функция запускается автоматически и сама чистит историю + строит новый график."""
    print(f"[{datetime.now()}] Запуск автогенерации расписания...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # === 1. АВТОМАТИЧЕСКОЕ УДАЛЕНИЕ СТАРЫХ СЛОТОВ И ГРАФИКОВ ===
    # Получаем сегодняшнюю дату в формате 'YYYY-MM-DD'
    today_str = str(datetime.now().date())

    try:
        # Сначала удаляем временные слоты, которые привязаны к прошедшим дням графикa
        cursor.execute("""
            DELETE FROM Time_Slots 
            WHERE schedule_id IN (SELECT id FROM Master_Schedule WHERE date < ?)
        """, (today_str,))

        # Затем удаляем сами прошедшие дни из графика мастеров
        cursor.execute("DELETE FROM Master_Schedule WHERE date < ?", (today_str,))

        conn.commit()
        print(f"🧹 База данных успешно очищена от прошедших слотов (всё, что до {today_str})")
    except sqlite3.OperationalError:
        # Если таблиц еще нет в базе, этот блок просто пропустится при самом первом старте
        pass
    # =========================================================

    # === 2. ДАЛЬШЕ ИДЕТ ВАШ СТАНДАРТНЫЙ КОД ГЕНЕРАЦИИ ГРАФИКА ===
    try:
        cursor.execute("SELECT id FROM Masters")
        masters = [row[0] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        print(f"❌ База данных {DB_NAME} или таблица Masters не найдена!")
        conn.close()
        return

    # Создаем таблицы графика, если их нет
    cursor.execute('''CREATE TABLE IF NOT EXISTS Master_Schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT, master_id INTEGER, date TEXT, UNIQUE(master_id, date))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Time_Slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT, schedule_id INTEGER, time_start TEXT, is_booked INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,          -- Telegram ID клиента
        service_id INTEGER,       -- Какая услуга
        master_id INTEGER,        -- Какой мастер
        date TEXT,                -- Дата визита (YYYY-MM-DD)
        time_start TEXT,          -- Время начала визита (HH:MM)
        created_at TEXT           -- Дата создания записи
    )''')

    # Планируем дни на неделю вперед (начиная со следующего дня)
    today = datetime.now().date()
    days_to_plan = [str(today + timedelta(days=i)) for i in range(1, 8)]

    master_work_days_count = {m_id: 0 for m_id in masters}

    for date in days_to_plan:
        for m_id in masters:
            if master_work_days_count[m_id] >= 3:
                continue

            if not has_service_conflict(cursor, m_id, date):
                try:
                    cursor.execute("INSERT INTO Master_Schedule (master_id, date) VALUES (?, ?)", (m_id, date))
                    schedule_id = cursor.lastrowid
                    master_work_days_count[m_id] += 1

                    # Генерируем новые 10-минутные слоты
                    slots = generate_10min_slots()
                    for slot in slots:
                        cursor.execute("INSERT INTO Time_Slots (schedule_id, time_start) VALUES (?, ?)",
                                       (schedule_id, slot))
                except sqlite3.IntegrityError:
                    pass  # График на этот день уже был создан ранее

    conn.commit()
    conn.close()
    print("✅ Новое расписание успешно обновлено.")


if __name__ == "__main__":
    build_schedule_job()
