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


def weekly_sessions_from_horario_columns(h1, h2):
    """
    Columnas HORARIO 1 / HORARIO 2 = códigos de franja semanal (M9, L11…).
    Cada columna rellena implica una sesión de 2 h a la semana en ese cuatrimestre.
    """
    count = sum(1 for h in (h1, h2) if horario_code_active(h))
    return count if count else 2


def semester_from_excel_column(value):
    """Columna «D» del Listado: 1 → primer cuatrimestre, 2 → segundo."""
    text = str(value).strip() if value is not None else ''
    if text in ('2', '2.0'):
        return SEMESTER_S2
    return SEMESTER_S1


def semester_plans_from_horario_columns(h1, h2, *, semester_col=1):
    """Devuelve [(semestre, sesiones/semana)] para una fila del Listado."""
    weekly = weekly_sessions_from_horario_columns(h1, h2)
    semester = semester_from_excel_column(semester_col)
    return [(semester, weekly)]
