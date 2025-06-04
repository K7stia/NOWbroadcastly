from aiogram.fsm.state import State, StatesGroup

class AddGroup(StatesGroup):
    waiting_name = State()
    selecting_channels = State()
    
class RenameGroup(StatesGroup):
    waiting_new_name = State()