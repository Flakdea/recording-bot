from aiogram.fsm.state import StatesGroup, State

class BookingStates(StatesGroup):
    choosing_category = State()  # Ожидание выбора категории услуг
    choosing_service = State()   # Ожидание выбора конкретной услуги
    choosing_date = State()      # Ожидание выбора даты
    choosing_master = State()    # Ожидание выбора мастера
    choosing_time = State()      # Ожидание выбора времени
