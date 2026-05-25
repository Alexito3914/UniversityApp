from datetime import time
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from horarios.models import (
    AcademicYear, Classroom, Course, DegreeProgram, Professor, ProfessorAvailability,
    Schedule, ScheduleEntry, Student, Subject, SubjectOffering, TimeSlotConfig, UserProfile,
)


class Command(BaseCommand):
    help = 'Carga datos de demostración para la entrega de Gestión de Horarios UCJC.'

    def handle(self, *args, **options):
        User = get_user_model()
        users = [
            ('decano', 'decano@ucjc.local', 'DEAN', True),
            ('profesor', 'ana.garcia@ucjc.local', 'PROF', False),
            ('estudiante', 'lucia.martin@ucjc.local', 'STUD', False),
            ('it', 'it@ucjc.local', 'IT', True),
        ]
        for username, email, role, staff in users:
            user, created = User.objects.get_or_create(username=username, defaults={'email': email, 'is_staff': staff, 'is_superuser': username == 'decano'})
            user.email = email
            user.is_staff = staff
            if username == 'decano':
                user.is_superuser = True
            user.set_password('ucjc1234')
            user.save()
            UserProfile.objects.update_or_create(user=user, defaults={'role': role})

        year, _ = AcademicYear.objects.update_or_create(name='2026-2027', defaults={'is_current': True})
        AcademicYear.objects.exclude(pk=year.pk).update(is_current=False)

        degrees_data = [
            ('INF', 'Ingeniería Informática'),
            ('ROB', 'Ingeniería Robótica'),
            ('TEL', 'Ingeniería Telemática'),
            ('DINFROB', 'Doble Grado Informática + Robótica'),
        ]
        degrees = {}
        for code, name in degrees_data:
            degrees[code], _ = DegreeProgram.objects.update_or_create(code=code, defaults={'name': name, 'is_active': True})

        courses = []
        for code, degree in degrees.items():
            max_course = 5 if code == 'DINFROB' else 4
            for number in range(1, max_course + 1):
                # Solo 4º curso va en tarde; el resto (incluido 5º del doble grado) va en mañana
                shift = 'AFTERNOON' if number == 4 else 'MORNING'
                course, _ = Course.objects.update_or_create(
                    degree_program=degree, academic_year=year, number=number, defaults={'shift': shift}
                )
                courses.append(course)

        # Franjas de MAÑANA (cursos 1º-3º): 09:00-11:00, 11:00-13:00, 13:00-15:00
        # Franjas de TARDE  (4º curso):     15:30-17:30, 17:30-19:30, 19:30-21:30
        morning_slots_data = [
            ('MON', time(9, 0), time(11, 0)), ('MON', time(11, 0), time(13, 0)), ('MON', time(13, 0), time(15, 0)),
            ('TUE', time(9, 0), time(11, 0)), ('TUE', time(11, 0), time(13, 0)), ('TUE', time(13, 0), time(15, 0)),
            ('WED', time(9, 0), time(11, 0)), ('WED', time(11, 0), time(13, 0)), ('WED', time(13, 0), time(15, 0)),
            ('THU', time(9, 0), time(11, 0)), ('THU', time(11, 0), time(13, 0)), ('THU', time(13, 0), time(15, 0)),
            ('FRI', time(9, 0), time(11, 0)), ('FRI', time(11, 0), time(13, 0)), ('FRI', time(13, 0), time(15, 0)),
        ]
        afternoon_slots_data = [
            ('MON', time(15, 30), time(17, 30)), ('MON', time(17, 30), time(19, 30)), ('MON', time(19, 30), time(21, 30)),
            ('TUE', time(15, 30), time(17, 30)), ('TUE', time(17, 30), time(19, 30)), ('TUE', time(19, 30), time(21, 30)),
            ('WED', time(15, 30), time(17, 30)), ('WED', time(17, 30), time(19, 30)), ('WED', time(19, 30), time(21, 30)),
            ('THU', time(15, 30), time(17, 30)), ('THU', time(17, 30), time(19, 30)), ('THU', time(19, 30), time(21, 30)),
            ('FRI', time(15, 30), time(17, 30)), ('FRI', time(17, 30), time(19, 30)), ('FRI', time(19, 30), time(21, 30)),
        ]
        # Limpiar franjas del año: ScheduleEntry usa timeslot con PROTECT
        ScheduleEntry.objects.filter(schedule__academic_year=year).delete()
        ProfessorAvailability.objects.filter(timeslot__academic_year=year).delete()
        TimeSlotConfig.objects.filter(academic_year=year).delete()
        slot_objs = []
        for day, start, end in morning_slots_data + afternoon_slots_data:
            slot = TimeSlotConfig.objects.create(
                academic_year=year, day_of_week=day, start_time=start, end_time=end, is_active=True
            )
            slot_objs.append(slot)

        classrooms = []
        for code, name, capacity in [('A101', 'Aula Polivalente A101', 45), ('LAB1', 'Laboratorio de Software', 28), ('ROB-LAB', 'Laboratorio de Robótica', 24)]:
            classroom, _ = Classroom.objects.update_or_create(code=code, defaults={'name': name, 'capacity': capacity})
            classrooms.append(classroom)

        profs = []
        for first, last, email in [
            ('Ana', 'García', 'ana.garcia@ucjc.local'),
            ('Luis', 'Romero', 'luis.romero@ucjc.local'),
            ('Marta', 'Santos', 'marta.santos@ucjc.local'),
            ('Carlos', 'Pérez', 'carlos.perez@ucjc.local'),
        ]:
            p, _ = Professor.objects.update_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'display_name': f'{last}, {first}',
                },
            )
            profs.append(p)

        for i, professor in enumerate(profs):
            if i < len(slot_objs):
                ProfessorAvailability.objects.update_or_create(professor=professor, timeslot=slot_objs[i], defaults={'status': 'BLOCKED'})
            for slot in slot_objs[i+1:i+3]:
                ProfessorAvailability.objects.update_or_create(professor=professor, timeslot=slot, defaults={'status': 'PREFERRED'})

        subjects_data = [
            ('PROG1', 'Programación I', True), ('BD', 'Bases de Datos', False), ('MAT', 'Matemáticas Aplicadas', True),
            ('ROB1', 'Fundamentos de Robótica', False), ('REDES', 'Redes y Sistemas', True), ('IA', 'Introducción a la Inteligencia Artificial', False),
        ]
        subjects = []
        for code, name, shared in subjects_data:
            subject, _ = Subject.objects.update_or_create(code=code, defaults={'name': name, 'weekly_sessions': 2, 'session_duration_hours': 2, 'is_shared': shared})
            if shared:
                subject.degree_programs.set([degrees['INF'], degrees['ROB'], degrees['DINFROB']])
            subjects.append(subject)

        main_courses = [c for c in courses if c.number == 1][:4]
        idx = 0
        for course in main_courses:
            for subject in subjects[:5]:
                SubjectOffering.objects.update_or_create(
                    subject=subject, course=course, group_name='Grupo A',
                    defaults={'professor': profs[idx % len(profs)], 'classroom': classrooms[idx % len(classrooms)]}
                )
                idx += 1

        Student.objects.update_or_create(email='lucia.martin@ucjc.local', defaults={'first_name': 'Lucía', 'last_name': 'Martín', 'course': main_courses[0]})
        Schedule.objects.get_or_create(name='Horario UCJC V2 - Primer Semestre', academic_year=year, defaults={'status': 'DRAFT'})
        self.stdout.write(self.style.SUCCESS('Datos demo creados. Usuarios: decano/profesor/estudiante/it. Contraseña: ucjc1234'))
