from aiogram.fsm.state import State, StatesGroup


class Triage(StatesGroup):
    q1_life_risk = State()      # есть ли риск жизни / травмы / суицид?
    q2_violence = State()       # есть ли физическое насилие / вымогательство?
    q3_systematic = State()     # это систематично (2+ раза)?


class Survey(StatesGroup):
    applicant_name       = State()  # шаг 1 — ФИО заявителя
    child_and_school     = State()  # шаг 2 — ФИО ребёнка + класс + школа + город одним сообщением
    incident_description = State()  # шаг 3 — описание ситуации (даты + что случилось)
    bully_age_group      = State()  # шаг 4а — возраст обидчика (кнопки)
    prior_actions        = State()  # шаг 4б — что уже делали (кнопки)
    confirm              = State()  # подтверждение перед генерацией
