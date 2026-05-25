"""Fixtures compartidos para tests del módulo horarios."""
from datetime import time

from django.contrib.auth.models import User

from horarios.models import (
    AcademicYear,
    Classroom,
    Course,
    DegreeProgram,
    Professor,
    Schedule,
    ScheduleEntry,
    Subject,
    SubjectOffering,
    TimeSlotConfig,
    UserProfile,
)
from horarios.services import create_schedule_entry


def create_user(username, role, email=None, password='ucjc1234'):
    user = User.objects.create_user(
        username=username,
        email=email or f'{username}@test.local',
        password=password,
    )
    UserProfile.objects.create(user=user, role=role)
    return user


def build_schedule_lab():
    """Escenario mínimo reutilizable: año, titulación, curso, profesores, franjas y horario."""
    year = AcademicYear.objects.create(name='2099-2100', is_current=True)
    degree = DegreeProgram.objects.create(code='INF-T', name='Informatica Test', is_active=True)
    course_morning = Course.objects.create(
        degree_program=degree, academic_year=year, number=1, shift='MORNING',
    )
    course_afternoon = Course.objects.create(
        degree_program=degree, academic_year=year, number=4, shift='AFTERNOON',
    )
    prof_1 = Professor.objects.create(first_name='Ana', last_name='Uno', email='ana.uno@test.local')
    prof_2 = Professor.objects.create(first_name='Luis', last_name='Dos', email='luis.dos@test.local')
    room_1 = Classroom.objects.create(code='T-101', name='Aula 101', capacity=30)
    room_2 = Classroom.objects.create(code='T-102', name='Aula 102', capacity=30)

    morning_slot = TimeSlotConfig.objects.create(
        academic_year=year, day_of_week='MON', start_time=time(9, 0), end_time=time(11, 0), is_active=True,
    )
    tue_morning = TimeSlotConfig.objects.create(
        academic_year=year, day_of_week='TUE', start_time=time(9, 0), end_time=time(11, 0), is_active=True,
    )
    afternoon_slot = TimeSlotConfig.objects.create(
        academic_year=year, day_of_week='MON', start_time=time(15, 30), end_time=time(17, 30), is_active=True,
    )
    invalid_slot = TimeSlotConfig.objects.create(
        academic_year=year, day_of_week='MON', start_time=time(8, 0), end_time=time(10, 0), is_active=True,
    )

    subj_a = Subject.objects.create(code='TST-A', name='Test A', weekly_sessions=2)
    subj_b = Subject.objects.create(code='TST-B', name='Test B', weekly_sessions=2)
    subj_c = Subject.objects.create(code='TST-C', name='Test C', weekly_sessions=12)

    offering_a = SubjectOffering.objects.create(
        subject=subj_a, course=course_morning, professor=prof_1, classroom=room_1, group_name='A',
    )
    offering_b = SubjectOffering.objects.create(
        subject=subj_b, course=course_morning, professor=prof_2, classroom=room_2, group_name='A',
    )
    schedule = Schedule.objects.create(name='Horario Test', academic_year=year, status='DRAFT')

    return {
        'year': year,
        'degree': degree,
        'course_morning': course_morning,
        'course_afternoon': course_afternoon,
        'prof_1': prof_1,
        'prof_2': prof_2,
        'room_1': room_1,
        'room_2': room_2,
        'morning_slot': morning_slot,
        'tue_morning': tue_morning,
        'afternoon_slot': afternoon_slot,
        'invalid_slot': invalid_slot,
        'subj_a': subj_a,
        'subj_b': subj_b,
        'subj_c': subj_c,
        'offering_a': offering_a,
        'offering_b': offering_b,
        'schedule': schedule,
    }


def add_schedule_entry(schedule, offering, timeslot):
    return create_schedule_entry(schedule, offering, timeslot)
