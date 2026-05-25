"""
Motor de generación y validación de horarios UCJC.

Restricciones duras (Hard Constraints):
- RD-05: Un profesor no puede impartir dos asignaturas al mismo tiempo.
- RD-12: Un aula no puede tener dos asignaturas al mismo tiempo.
- RD-08: Un curso no puede tener dos asignaturas al mismo tiempo.
- RD-04/RD-U01: Cursos 1º-3º → solo turno mañana (<13:00). 4º curso → solo turno tarde (≥13:00).
- Máximo 20 horas lectivas semanales por curso.
- Día libre opcional: se excluye un día de la semana para todas las asignaturas de la misma titulación.

Soft Constraints:
- Se priorizan franjas preferentes del profesor.
- Se favorecen clases consecutivas en el mismo día.
"""

import datetime
from collections import defaultdict
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Count

from .models import ProfessorAvailability, ScheduleEntry, SubjectOffering, TimeSlotConfig

MORNING_START = datetime.time(9, 0)
MORNING_END = datetime.time(15, 0)
AFTERNOON_START = datetime.time(15, 30)
AFTERNOON_END = datetime.time(21, 30)


def _is_morning_slot(slot):
    return MORNING_START <= slot.start_time and slot.end_time <= MORNING_END


def _is_afternoon_slot(slot):
    return AFTERNOON_START <= slot.start_time and slot.end_time <= AFTERNOON_END


def _course_slot_conflict(offering, other_offering):
    """Un curso no puede tener dos clases a la vez, salvo 4º con grupos de especialidad distintos."""
    if offering.course_id != other_offering.course_id:
        return False
    if offering.course.number >= 4:
        return offering.group_name == other_offering.group_name
    return True


def _slot_conflicts(schedule, offering, slot):
    qs = ScheduleEntry.objects.filter(schedule=schedule, timeslot=slot).select_related(
        'subject_offering__professor', 'subject_offering__classroom', 'subject_offering__course'
    )
    for entry in qs:
        other = entry.subject_offering
        if other.professor_id == offering.professor_id:
            return True
        if other.classroom_id == offering.classroom_id:
            return True
        if _course_slot_conflict(offering, other):
            return True
    return False


def validate_schedule_entry(schedule, offering, slot, exclude_pk=None):
    """Devuelve una lista de errores para una entrada de horario (RF-02, RD-05, RD-12)."""
    errors = []
    qs = ScheduleEntry.objects.filter(schedule=schedule, timeslot=slot)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    clash_prof = (
        qs.filter(subject_offering__professor=offering.professor)
        .select_related('subject_offering__subject', 'subject_offering__course__degree_program')
        .first()
    )
    if clash_prof:
        other = clash_prof.subject_offering
        deg = other.course.degree_program.code
        subj_code = other.subject.code
        day_label = clash_prof.timeslot.get_day_of_week_display() if clash_prof.timeslot_id else ''
        range_label = ''
        if clash_prof.timeslot_id:
            ts_sl = clash_prof.timeslot
            range_label = f'{ts_sl.start_time.strftime("%H:%M")}-{ts_sl.end_time.strftime("%H:%M")}'
        slot_hint = f' ({day_label} {range_label})'.rstrip()
        errors.append(
            f'Conflicto: el profesor ya imparte '
            f'«{deg} · {subj_code} · {other.course.number}º» en esta franja{slot_hint} '
            f'(dentro de este mismo horario, cuenta cualquier titulación). '
            'No puede dar dos clases a la vez.'
        )
    if qs.filter(subject_offering__classroom=offering.classroom).exists():
        errors.append('El aula ya está ocupada en esa franja.')
    course_clash = qs.filter(subject_offering__course=offering.course).select_related(
        'subject_offering__course'
    )
    if offering.course.number >= 4:
        course_clash = course_clash.filter(subject_offering__group_name=offering.group_name)
    if course_clash.exists():
        errors.append('El curso/grupo ya tiene otra clase en esa franja.')
    if ProfessorAvailability.objects.filter(professor=offering.professor, timeslot=slot, status='BLOCKED').exists():
        errors.append('El profesor ha marcado esta franja como indisponible.')

    # Shift check
    is_afternoon_slot = _is_afternoon_slot(slot)
    is_morning_slot = _is_morning_slot(slot)
    course_number = offering.course.number
    if is_afternoon_slot and course_number < 4:
        errors.append('Las franjas de tarde solo están permitidas para 4º curso.')
    if is_morning_slot and course_number >= 4:
        errors.append('El 4º curso solo puede asignarse en franjas de tarde.')
    if not is_morning_slot and not is_afternoon_slot:
        errors.append('La franja no está dentro del horario permitido (09:00-15:00 o 15:30-21:30).')

    return errors


def suggest_slots_for_offering(schedule, offering, limit=5, free_day=None):
    """Devuelve una lista de franjas sugeridas para una oferta sin conflictos."""
    all_slots = list(
        TimeSlotConfig.objects.filter(academic_year=schedule.academic_year, is_active=True).order_by('day_of_week', 'start_time')
    )
    slots_pool = [s for s in all_slots if _is_afternoon_slot(s)] if offering.course.number >= 4 else [s for s in all_slots if _is_morning_slot(s)]
    if free_day:
        slots_pool = [s for s in slots_pool if s.day_of_week != free_day]

    preferred = set(
        ProfessorAvailability.objects.filter(
            professor=offering.professor,
            status='PREFERRED',
            timeslot__in=slots_pool,
        ).values_list('timeslot_id', flat=True)
    )
    blocked = set(
        ProfessorAvailability.objects.filter(
            professor=offering.professor,
            status='BLOCKED',
            timeslot__in=slots_pool,
        ).values_list('timeslot_id', flat=True)
    )

    ranked = sorted(
        slots_pool,
        key=lambda s: (0 if s.pk in preferred else 1, s.day_of_week, s.start_time),
    )
    suggestions = []
    for slot in ranked:
        if slot.pk in blocked:
            continue
        if validate_schedule_entry(schedule, offering, slot):
            continue
        suggestions.append(slot)
        if len(suggestions) >= limit:
            break
    return suggestions


def create_schedule_entry(schedule, offering, slot):
    """Capa única para crear entradas respetando validaciones de conflicto."""
    errors = validate_schedule_entry(schedule, offering, slot)
    if errors:
        raise ValidationError(errors)
    return ScheduleEntry.objects.create(schedule=schedule, subject_offering=offering, timeslot=slot)


def get_generation_report(schedule):
    """Resumen de sesiones planificadas vs requeridas para el informe (RF-03)."""
    rows = []
    if not schedule:
        return rows
    offerings = SubjectOffering.objects.filter(
        course__academic_year=schedule.academic_year
    ).select_related('subject', 'course__degree_program', 'professor', 'classroom')
    planned_counts = dict(
        ScheduleEntry.objects.filter(schedule=schedule)
        .values('subject_offering_id')
        .annotate(total=Count('id'))
        .values_list('subject_offering_id', 'total')
    )
    for offering in offerings:
        required = offering.subject.weekly_sessions
        planned = planned_counts.get(offering.pk, 0)
        rows.append({
            'offering': offering,
            'subject_code': offering.subject.code,
            'subject_name': offering.subject.name,
            'course': str(offering.course),
            'teacher': str(offering.professor),
            'shared': offering.subject.is_shared,
            'required': required,
            'scheduled': planned,
            'ok': planned >= required,
        })
    return rows


@transaction.atomic
def generate_schedule_entries(schedule, clear_existing=False, free_day=None, degree_id=None, course_id=None, course_number=None):
    """
    Generador automático de horarios basado en restricciones duras.

    Parámetros:
        schedule       — instancia de Schedule (DRAFT)
        clear_existing — si True, borra las entradas previas
        free_day       — código de día a dejar libre (ej: 'MON'), o None
        degree_id      — id de titulación a generar (None = todas)
        course_id      — id de Course (None = todos los cursos del año académico activo del horario)
        course_number  — 1-4: todos los cursos de ese año en todas (o una) titulación

    Restricciones aplicadas:
        - 1º-3º solo mañana, 4º solo tarde
        - Máximo 20 horas semanales por Course
        - Día libre por titulación si se especifica
        - No conflictos de profesor, aula ni curso en el mismo slot
        - Nunca usa franjas bloqueadas por el profesor
        - Prioriza franjas preferentes
    """
    if clear_existing:
        ScheduleEntry.objects.filter(schedule=schedule).delete()

    # Franjas del año académico, separadas por turno
    all_slots = list(TimeSlotConfig.objects.filter(
        academic_year=schedule.academic_year,
        is_active=True,
    ).order_by('day_of_week', 'start_time'))

    morning_slots = [s for s in all_slots if _is_morning_slot(s)]
    afternoon_slots = [s for s in all_slots if _is_afternoon_slot(s)]

    # Disponibilidad del profesorado
    preferred = defaultdict(set)
    blocked = defaultdict(set)
    for av in ProfessorAvailability.objects.select_related('timeslot'):
        if av.status == 'PREFERRED':
            preferred[av.professor_id].add(av.timeslot_id)
        elif av.status == 'BLOCKED':
            blocked[av.professor_id].add(av.timeslot_id)

    # Contadores de horas semanales por Course (2h por sesión según RD-01)
    hours_per_course = defaultdict(int)
    for e in ScheduleEntry.objects.filter(schedule=schedule).select_related('subject_offering__course'):
        hours_per_course[e.subject_offering.course_id] += 2
    MAX_HOURS = 20

    # Ofertas ordenadas: primero las más difíciles de encajar (más sesiones)
    offerings_qs = SubjectOffering.objects.filter(
        course__academic_year=schedule.academic_year
    )
    if degree_id:
        offerings_qs = offerings_qs.filter(course__degree_program_id=degree_id)
    if course_id:
        offerings_qs = offerings_qs.filter(course_id=course_id)
    elif course_number is not None:
        offerings_qs = offerings_qs.filter(course__number=course_number)
    offerings = list(offerings_qs.select_related('subject', 'course', 'professor', 'classroom').order_by(
        '-subject__weekly_sessions', 'course__degree_program__code', 'course__number', 'subject__code'
    ))

    created = 0
    unresolved = []

    existing_entries = list(
        ScheduleEntry.objects.filter(schedule=schedule).select_related(
            'subject_offering__professor',
            'subject_offering__classroom',
            'subject_offering__course',
            'timeslot',
        )
    )
    busy_professor = {(e.timeslot_id, e.subject_offering.professor_id) for e in existing_entries}
    busy_classroom = {(e.timeslot_id, e.subject_offering.classroom_id) for e in existing_entries}
    busy_course = set()
    for e in existing_entries:
        cnum = e.subject_offering.course.number
        gname = e.subject_offering.group_name if cnum >= 4 else ''
        busy_course.add((e.timeslot_id, e.subject_offering.course_id, gname))
    planned_per_offering = defaultdict(int)
    for e in existing_entries:
        planned_per_offering[e.subject_offering_id] += 1

    for offering in offerings:
        existing = planned_per_offering[offering.pk]
        remaining = max(offering.subject.weekly_sessions - existing, 0)
        if remaining == 0:
            continue

        # Selección de slots según turno del curso
        course_number = offering.course.number
        slots_pool = afternoon_slots if course_number >= 4 else morning_slots

        # Excluir día libre si se especificó (aplica a toda la titulación)
        if free_day:
            slots_pool = [s for s in slots_pool if s.day_of_week != free_day]

        # Excluir slots bloqueados por el profesor
        candidate_slots = [s for s in slots_pool if s.pk not in blocked[offering.professor_id]]

        # Ordenar: preferentes primero, luego por día y hora (soft constraints)
        candidate_slots = sorted(
            candidate_slots,
            key=lambda s: (
                0 if s.pk in preferred[offering.professor_id] else 1,
                s.day_of_week,
                s.start_time,
            )
        )

        for slot in candidate_slots:
            if remaining == 0:
                break
            # Respetar máximo de 20h semanales por curso
            if hours_per_course[offering.course_id] + 2 > MAX_HOURS:
                break
            course_key = (slot.pk, offering.course_id, offering.group_name if course_number >= 4 else '')
            if (
                (slot.pk, offering.professor_id) in busy_professor
                or (slot.pk, offering.classroom_id) in busy_classroom
                or course_key in busy_course
            ):
                continue
            try:
                create_schedule_entry(schedule, offering, slot)
            except ValidationError:
                continue
            busy_professor.add((slot.pk, offering.professor_id))
            busy_classroom.add((slot.pk, offering.classroom_id))
            busy_course.add(course_key)
            planned_per_offering[offering.pk] += 1
            created += 1
            remaining -= 1
            hours_per_course[offering.course_id] += 2

        if remaining:
            unresolved.append({'offering': offering, 'missing': remaining})

    return {'created': created, 'unresolved': unresolved, 'total_offerings': len(offerings)}
