"""Constantes y utilidades de cuatrimestres académicos."""

SEMESTER_S1 = 'S1'
SEMESTER_S2 = 'S2'

SEMESTER_LABELS = {
    SEMESTER_S1: 'PRIMER SEMESTRE',
    SEMESTER_S2: 'SEGUNDO SEMESTRE',
}

EXCEL_SHEET_TITLES = {
    SEMESTER_S1: 'HORARIOS 1º CUATRIMESTRE',
    SEMESTER_S2: 'HORARIOS 2º CUATRIMESTRE',
}


def horario_code_active(value):
    if value is None:
        return False
    text = str(value).strip()
    return text not in ('', 'True', 'False', 'None')


def semester_plans_from_horario_columns(h1, h2):
    """Deriva cuatrimestres y sesiones/semana según columnas HORARIO 1 / HORARIO 2 del Excel."""
    plans = []
    if horario_code_active(h1):
        plans.append((SEMESTER_S1, 1))
    if horario_code_active(h2):
        plans.append((SEMESTER_S2, 1))
    if not plans:
        weekly = 2 if horario_code_active(h1) or horario_code_active(h2) else 2
        plans.append((SEMESTER_S1, weekly))
    return plans
