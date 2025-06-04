from aiogram.fsm.state import StatesGroup, State

class ManualMonitorState(StatesGroup):
    selecting_category = State()
    selecting_model = State()
    selecting_publish_mode = State()
    selecting_targets = State()
    toggle_moderation = State()
    toggle_rewrite = State()
    confirm_launch = State()
    toggle_skip_forwards = State()  

    editing_trim_lines = State()
    editing_trim_phrases = State()

class SourceSignatureState(StatesGroup):
    editing = State()

class StopWordsState(StatesGroup):
    editing = State()
    adding = State()
    deleting = State()

class ScenarioState(StatesGroup):
    entering_name = State()
    entering_note = State()
    selecting_groups = State()
    toggling_rewrite = State()
    toggling_moderation = State()
    toggling_skip_forwards = State()
    confirming = State()

class ScenarioCreateState(StatesGroup):
    entering_name = State()
    selecting_groups = State()
    selecting_options = State()
    selecting_schedule_mode = State()
    selecting_targets = State()
    entering_fixed_time = State()         
    entering_interval_start = State()      
    entering_interval_end = State()        
    entering_loop_delay = State()    
    entering_note = State()
    selecting_media = State()
    selecting_model = State() 

