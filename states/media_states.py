from aiogram.fsm.state import StatesGroup, State

class AddMediaState(StatesGroup):
    waiting_forward = State()         # для пересланого повідомлення або @username телеграм-каналу
    waiting_facebook_id = State()     # для введення Facebook Page ID
