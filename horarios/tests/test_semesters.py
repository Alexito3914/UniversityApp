from django.test import SimpleTestCase

from horarios.semesters import (
    SEMESTER_S1,
    SEMESTER_S2,
    semester_from_excel_column,
    semester_plans_from_horario_columns,
    weekly_sessions_from_horario_columns,
)


class SemesterUtilsTests(SimpleTestCase):
    def test_weekly_sessions_counts_slot_codes(self):
        self.assertEqual(weekly_sessions_from_horario_columns('M9', 'J9'), 2)
        self.assertEqual(weekly_sessions_from_horario_columns('M9', None), 1)
        self.assertEqual(weekly_sessions_from_horario_columns(None, None), 2)

    def test_semester_from_excel_d_column(self):
        self.assertEqual(semester_from_excel_column(1), SEMESTER_S1)
        self.assertEqual(semester_from_excel_column('1'), SEMESTER_S1)
        self.assertEqual(semester_from_excel_column(2), SEMESTER_S2)
        self.assertEqual(semester_from_excel_column('2'), SEMESTER_S2)

    def test_semester_plans_uses_d_column_and_two_weekly_sessions(self):
        plans = semester_plans_from_horario_columns('M9', 'J9', semester_col=1)
        self.assertEqual(plans, [(SEMESTER_S1, 2)])

        plans = semester_plans_from_horario_columns('L11', 'X11', semester_col=2)
        self.assertEqual(plans, [(SEMESTER_S2, 2)])

    def test_one_offering_per_row_not_both_semesters(self):
        plans = semester_plans_from_horario_columns('M9', 'J9', semester_col=2)
        self.assertEqual(len(plans), 1)
