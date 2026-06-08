from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_for_prompt = State()
    waiting_for_ai_model = State()
    waiting_for_ai_key = State()
    waiting_for_blacklist_id = State()
    waiting_for_qr_confirm = State()
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_2fa = State()
    waiting_for_reply_delay = State()
    waiting_for_ignored_words = State()
    waiting_for_context_limit = State()
    waiting_for_owner_bio = State()
    waiting_for_chat_note_id = State()
    waiting_for_chat_note_text = State()
    waiting_for_debounce = State()
    waiting_for_owner_pause = State()
    waiting_for_stop_word = State()
    waiting_for_resume_word = State()
    waiting_for_toxicity_words = State()
