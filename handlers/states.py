from aiogram.fsm.state import State, StatesGroup


class Triage(StatesGroup):
    q1_life_risk = State()      # есть ли риск жизни / травмы / суицид?
    q2_violence = State()       # есть ли физическое насилие / вымогательство?
    q3_systematic = State()     # это систематично (2+ раза)?


class Survey(StatesGroup):
    applicant_name = State()
    child_name = State()
    child_class = State()
    school_name = State()
    city = State()
    bully_age_group = State()
    incident_dates = State()
    incident_description = State()
    witnesses = State()
    has_evidence = State()
    prior_actions = State()
    confirm = State()
