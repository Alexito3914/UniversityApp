from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from horarios.excel_import import HorariosExcelImporter
from horarios.models import SubjectOffering

from .base import create_user

EXCEL = Path(__file__).resolve().parents[2] / 'data' / 'HORARIOS_25_26.xlsx'
ORGANIZED = Path(__file__).resolve().parents[2] / 'data' / 'listado_eps_4_grados.xlsx'


class ExcelImportWebTests(TestCase):
    def setUp(self):
        self.dean = create_user('dean_xls', 'DEAN')
        from horarios.models import AcademicYear
        self.year, _ = AcademicYear.objects.get_or_create(name='2026-2027', defaults={'is_current': True})

    def test_dean_can_open_import_page(self):
        self.client.login(username='dean_xls', password='ucjc1234')
        response = self.client.get(reverse('horarios:excel_import'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Subir listado')

    def test_import_tomas_excel_via_service(self):
        if not EXCEL.exists():
            self.skipTest('Excel de demo no encontrado')
        stats = HorariosExcelImporter('2026-2027', clear_eps=True, auto_generate=False).run(EXCEL)
        self.assertGreater(stats['offerings'], 50)
        self.assertIn('INF', stats['degrees'])

    def test_import_organized_excel(self):
        if not ORGANIZED.exists():
            self.skipTest('Excel organizado no encontrado')
        before = SubjectOffering.objects.count()
        stats = HorariosExcelImporter('2026-2027', clear_eps=True, auto_generate=False).run(ORGANIZED)
        self.assertGreater(stats['offerings'], before or 100)
        self.assertGreaterEqual(stats['rows_processed'], 200)
