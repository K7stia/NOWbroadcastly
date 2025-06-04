from aiogram.fsm.state import StatesGroup, State

class AddChannelState(StatesGroup):
    waiting_forward = State()
