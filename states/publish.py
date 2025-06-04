from aiogram.fsm.state import State, StatesGroup

class PublishNews(StatesGroup):
    waiting_content = State()
    waiting_options = State()
    waiting_schedule = State()
