from aiogram.fsm.state import StatesGroup, State

class SignatureState(StatesGroup):
    waiting_text = State()
    waiting_signature = State()