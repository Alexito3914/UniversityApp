"""
Importa titulaciones, asignaturas, profesores y ofertas desde HORARIOS_25_26.xlsx (Listado).
Opcionalmente carga la cuadrícula de referencia del decanato (--apply-schedule).
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from horarios.excel_import import ExcelImportError, HorariosExcelImporter

DEFAULT_EXCEL = Path(__file__).resolve().parents[3] / 'data' / 'HORARIOS_25_26.xlsx'


class Command(BaseCommand):
    help = 'Importa asignaturas/profesores/ofertas desde Excel (hoja Listado o Listado 4 grados).'

    def add_arguments(self, parser):
        parser.add_argument('--file', default=str(DEFAULT_EXCEL), help='Ruta al Excel del decanato')
        parser.add_argument('--year', default='2026-2027', help='Año académico')
        parser.add_argument(
            '--apply-schedule',
            action='store_true',
            help='Carga la cuadrícula de las hojas HORARIOS 1º/2º CUATRIMESTRE',
        )
        parser.add_argument(
            '--clear-eps',
            action='store_true',
            help='Borra ofertas/sesiones EPS (INF/ROB/TEL/DINFROB) antes de importar',
        )
        parser.add_argument(
            '--auto-generate',
            action='store_true',
            help='Genera horarios S1/S2 automáticamente tras importar',
        )

    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.exists():
            raise CommandError(f'No se encuentra el archivo: {path}')

        try:
            stats = HorariosExcelImporter(
                options['year'],
                clear_eps=options['clear_eps'],
                apply_schedule=options['apply_schedule'],
                auto_generate=options['auto_generate'],
            ).run(path)
        except ExcelImportError as exc:
            raise CommandError(str(exc)) from exc

        msg = (
            f'Importación completada · año {stats["year"]} · '
            f'{stats["subjects_new"]} asignaturas nuevas · {stats["offerings"]} ofertas · '
            f'titulaciones: {", ".join(stats["degrees"])}'
        )
        if stats['schedule_grid_cells']:
            msg += f' · {stats["schedule_grid_cells"]} celdas del Excel'
        if stats['generated']:
            for sem, data in stats['generated'].items():
                msg += f' · {sem}: {data["created"]} sesiones generadas'
        self.stdout.write(self.style.SUCCESS(msg))
