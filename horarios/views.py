"""
Views principales del sistema de gestión de horarios UCJC.
Cada vista requiere autenticación y el acceso se restringe según rol (RBAC).
"""

import csv
import json
import logging
import datetime
import re
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.urls import reverse

from .excel_grid import build_schedule_workbook, workbook_to_bytes
from .forms import ProfessorAvailabilityForm, ScheduleEntryForm, ScheduleForm, SubjectOfferingForm
from .models import (
    AcademicYear, Course, DegreeProgram, Enrollment, Professor, Schedule,
    ScheduleEntry, Student, Subject, SubjectOffering, TimeSlotConfig, UserProfile,
)
from .services import (
    AFTERNOON_END,
    AFTERNOON_START,
    MORNING_END,
    MORNING_START,
    create_schedule_entry,
    generate_schedule_entries,
    format_no_offerings_message,
    get_generation_report,
    suggest_slots_for_offering,
    validate_schedule_entry,
)
from .services_notifications import (
    notify_schedule_approved,
    notify_schedule_rejected,
    notify_schedule_reopened,
    notify_schedule_submitted,
)

logger = logging.getLogger('horarios.audit')

STUDENT_COURSE_SESSION_KEY = 'student_course_id'
STUDENT_GROUP_SESSION_KEY = 'student_group_name'


def _get_student_course(request):
    course_id = request.session.get(STUDENT_COURSE_SESSION_KEY)
    if not course_id:
        return None
    return Course.objects.select_related('degree_program', 'academic_year').filter(pk=course_id).first()


def _set_student_course(request, course):
    request.session[STUDENT_COURSE_SESSION_KEY] = course.pk


def _clear_student_course(request):
    request.session.pop(STUDENT_COURSE_SESSION_KEY, None)
    request.session.pop(STUDENT_GROUP_SESSION_KEY, None)


def _get_student_group(request):
    return request.session.get(STUDENT_GROUP_SESSION_KEY) or None


def _set_student_group(request, group_name):
    if group_name:
        request.session[STUDENT_GROUP_SESSION_KEY] = group_name
    else:
        request.session.pop(STUDENT_GROUP_SESSION_KEY, None)


def _published_schedule(academic_year):
    if not academic_year:
        return None
    return Schedule.objects.filter(
        academic_year=academic_year,
        status='APPROVED',
    ).order_by('-updated_at').first()


def _schedule_for_student(course):
    return _published_schedule(course.academic_year)


def _course_group_choices(course):
    if not course:
        return []
    return list(
        course.subject_offerings.exclude(group_name='')
        .values_list('group_name', flat=True)
        .distinct()
        .order_by('group_name')
    )


def _student_schedule_redirect(request):
    if _get_student_course(request):
        return redirect('horarios:student_my_schedule')
    return redirect('horarios:student_schedule_setup')


def _is_allowed_slot_range(start_time, end_time):
    morning_ok = MORNING_START <= start_time and end_time <= MORNING_END
    afternoon_ok = AFTERNOON_START <= start_time and end_time <= AFTERNOON_END
    return morning_ok or afternoon_ok


DAY_ORDER = ['MON', 'TUE', 'WED', 'THU', 'FRI']
DAY_LABELS = {
    'MON': 'Lunes', 'TUE': 'Martes', 'WED': 'Miércoles', 'THU': 'Jueves', 'FRI': 'Viernes',
}


def _build_availability_grid(timeslots, form):
    base_times = sorted({(ts.start_time, ts.end_time) for ts in timeslots})
    morning_times = [t for t in base_times if MORNING_START <= t[0] < MORNING_END]
    afternoon_times = [t for t in base_times if AFTERNOON_START <= t[0] < AFTERNOON_END]
    slot_index = {(ts.day_of_week, ts.start_time, ts.end_time): ts for ts in timeslots}

    def build_rows(time_pairs):
        rows = []
        for time_pair in time_pairs:
            cells = []
            for day in DAY_ORDER:
                ts = slot_index.get((day, time_pair[0], time_pair[1]))
                if ts and form:
                    cells.append({'timeslot': ts, 'field': form[f'ts_{ts.pk}']})
                else:
                    cells.append(None)
            rows.append({'time_pair': time_pair, 'cells': cells})
        return rows

    return {
        'day_order': DAY_ORDER,
        'day_labels': DAY_LABELS,
        'sections': [
            {'label': 'Turno de mañana', 'shift': 'morning', 'rows': build_rows(morning_times)},
            {'label': 'Turno de tarde', 'shift': 'afternoon', 'rows': build_rows(afternoon_times)},
        ],
    }


def _get_user_role(request):
    try:
        return request.user.userprofile.role
    except UserProfile.DoesNotExist:
        return None


def _role_label(role):
    return dict(UserProfile.ROLE_CHOICES).get(role, 'Usuario')


def _can_manage(role):
    return role in ('DEAN', 'IT')


def _audit(request, action, detail):
    user_id = request.user.pk if request.user.is_authenticated else 'anonymous'
    session_key = request.session.session_key or 'no-session'
    logger.info('AUDIT action=%s user_id=%s session=%s detail=%s', action, user_id, session_key, detail)


@login_required
def home(request):
    role = _get_user_role(request)
    if role == 'STUD':
        return _student_schedule_redirect(request)
    current_year = AcademicYear.objects.filter(is_current=True).first()
    latest_schedule = Schedule.objects.select_related('academic_year').order_by('-created_at').first()
    report_rows = get_generation_report(latest_schedule)[:5] if latest_schedule else []
    context = {
        'active_page': 'inicio',
        'total_titulaciones': DegreeProgram.objects.filter(is_active=True).count(),
        'total_cursos': Course.objects.count(),
        'total_profesores': Professor.objects.count(),
        'total_horarios': Schedule.objects.count(),
        'total_asignaturas': Subject.objects.count(),
        'horarios_draft': Schedule.objects.filter(status='DRAFT').count(),
        'horarios_review': Schedule.objects.filter(status='REVIEW').count(),
        'horarios_approved': Schedule.objects.filter(status='APPROVED').count(),
        'current_year': current_year,
        'latest_schedule': latest_schedule,
        'report_rows': report_rows,
        'user_role': role,
        'role_label': _role_label(role),
    }
    return render(request, 'horarios/home.html', context)


@login_required
def dashboard(request):
    schedules = Schedule.objects.select_related('academic_year').annotate(entries_count=Count('entries')).order_by('-created_at')[:10]
    degrees = DegreeProgram.objects.filter(is_active=True).prefetch_related('courses')
    context = {
        'active_page': 'inicio',
        'schedules': schedules,
        'degrees': degrees,
        'user_role': _get_user_role(request),
    }
    return render(request, 'horarios/dashboard.html', context)


@login_required
def schedule_list(request):
    role = _get_user_role(request)
    if role == 'STUD':
        return _student_schedule_redirect(request)
    if role == 'PROF':
        return redirect('horarios:professor_my_schedule')
    status = request.GET.get('status', '')
    year = request.GET.get('year', '')
    q = request.GET.get('q', '')
    schedules = Schedule.objects.select_related('academic_year').annotate(entries_count=Count('entries')).order_by('-created_at')
    if status:
        schedules = schedules.filter(status=status)
    if year:
        schedules = schedules.filter(academic_year_id=year)
    if q:
        schedules = schedules.filter(name__icontains=q)
    if status == 'REVIEW':
        active_page = 'workflow'
    elif status == 'DRAFT':
        active_page = 'generador'
    else:
        active_page = 'horarios'
    context = {
        'active_page': active_page,
        'schedules': schedules,
        'years': AcademicYear.objects.all(),
        'selected_status': status,
        'selected_year': year,
        'q': q,
        'status_choices': Schedule.STATUS_CHOICES,
        'user_role': role,
        'can_manage': _can_manage(role),
    }
    return render(request, 'horarios/schedule_list.html', context)


@ensure_csrf_cookie
@login_required
def schedule_detail(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    role = _get_user_role(request)
    is_student_view = role == 'STUD'
    is_professor_view = role == 'PROF'
    student_course = _get_student_course(request) if is_student_view else None
    student_group = _get_student_group(request) if is_student_view else None
    linked_professor = None
    if is_professor_view:
        linked_professor = Professor.objects.filter(email=request.user.email).first()

    if is_student_view:
        if not student_course:
            return redirect('horarios:student_schedule_setup')
        if schedule.academic_year_id != student_course.academic_year_id:
            messages.error(request, 'Este horario no corresponde a tu año académico.')
            return redirect('horarios:student_my_schedule')
        published_ids = Schedule.objects.filter(
            academic_year=student_course.academic_year,
            status='APPROVED',
        ).values_list('pk', flat=True)
        if not published_ids:
            messages.warning(request, 'Este horario aún no está publicado.')
            return redirect('horarios:student_my_schedule')
        degree_filter = str(student_course.degree_program_id)
        course_filter = str(student_course.pk)
        professor_filter = None
        entries_qs = ScheduleEntry.objects.filter(schedule_id__in=published_ids)
    elif is_professor_view:
        if not linked_professor:
            messages.error(request, 'Tu usuario no está vinculado a un perfil de profesor.')
            return redirect('horarios:home')
        published_ids = Schedule.objects.filter(
            academic_year=schedule.academic_year,
            status='APPROVED',
        ).values_list('pk', flat=True)
        if not published_ids:
            messages.warning(request, 'Solo puedes consultar horarios publicados.')
            return redirect('horarios:professor_my_schedule')
        professor_filter = str(linked_professor.pk)
        degree_filter = request.GET.get('degree')
        course_filter = request.GET.get('course')
        entries_qs = ScheduleEntry.objects.filter(schedule_id__in=published_ids)
    else:
        degree_filter = request.GET.get('degree')
        course_filter = request.GET.get('course')
        professor_filter = request.GET.get('professor')
        entries_qs = schedule.entries.all()

    entries_qs = entries_qs.select_related(
        'subject_offering__subject', 'subject_offering__professor',
        'subject_offering__classroom', 'subject_offering__course__degree_program', 'timeslot'
    )
    if degree_filter:
        entries_qs = entries_qs.filter(subject_offering__course__degree_program_id=degree_filter)
    if course_filter:
        entries_qs = entries_qs.filter(subject_offering__course_id=course_filter)
    if professor_filter:
        entries_qs = entries_qs.filter(subject_offering__professor_id=professor_filter)
    if is_student_view and student_group:
        entries_qs = entries_qs.filter(
            Q(subject_offering__group_name=student_group) |
            Q(subject_offering__subject__is_shared=True)
        )

    day_order = ['MON', 'TUE', 'WED', 'THU', 'FRI']
    day_labels = {'MON': 'Lunes', 'TUE': 'Martes', 'WED': 'Miércoles', 'THU': 'Jueves', 'FRI': 'Viernes'}
    base_times = sorted(
        set(
            TimeSlotConfig.objects.filter(academic_year=schedule.academic_year, is_active=True)
            .values_list('start_time', 'end_time')
        )
    )
    morning_times = [t for t in base_times if MORNING_START <= t[0] < MORNING_END]
    afternoon_times = [t for t in base_times if AFTERNOON_START <= t[0] < AFTERNOON_END]
    timetable = {time_pair: {day: [] for day in day_order} for time_pair in base_times}
    entries = list(entries_qs)
    for entry in entries:
        key = (entry.timeslot.start_time, entry.timeslot.end_time)
        if key in timetable and entry.timeslot.day_of_week in timetable[key]:
            timetable[key][entry.timeslot.day_of_week].append(entry)

    selected_degree_obj = DegreeProgram.objects.filter(pk=degree_filter).first() if degree_filter else None
    selected_course_obj = Course.objects.select_related('degree_program').filter(pk=course_filter).first() if course_filter else None
    sibling_schedule = Schedule.objects.filter(
        academic_year=schedule.academic_year,
    ).exclude(pk=schedule.pk).order_by('semester').first()
    context = {
        'active_page': 'horarios',
        'schedule': schedule,
        'sibling_schedule': sibling_schedule,
        'timetable': timetable,
        'morning_times': morning_times,
        'afternoon_times': afternoon_times,
        'day_order': day_order,
        'day_labels': day_labels,
        'base_times': base_times,
        'degrees': DegreeProgram.objects.filter(is_active=True),
        'academic_years': AcademicYear.objects.order_by('-name'),
        'courses': Course.objects.select_related('degree_program').filter(academic_year=schedule.academic_year),
        'professors': Professor.objects.all(),
        'selected_degree': degree_filter,
        'selected_degree_obj': selected_degree_obj,
        'selected_course': course_filter,
        'selected_course_obj': selected_course_obj,
        'selected_professor': professor_filter,
        'report_rows': get_generation_report(schedule),
        'user_role': role,
        'can_manage': _can_manage(role) and not is_student_view and not is_professor_view,
        'is_student_view': is_student_view,
        'is_professor_view': is_professor_view,
        'student_course': student_course,
        'student_group': student_group,
        'linked_professor': linked_professor,
    }
    return render(request, 'horarios/schedule_detail.html', context)


@login_required
def student_schedule_setup(request):
    role = _get_user_role(request)
    if role != 'STUD':
        return redirect('horarios:home')

    current_year = AcademicYear.objects.filter(is_current=True).first()
    degrees = DegreeProgram.objects.filter(is_active=True).order_by('code')
    course_numbers = list(range(1, 5))
    selected = _get_student_course(request)

    group_choices = _course_group_choices(selected) if selected else []
    form_group_choices = group_choices
    if request.method == 'POST':
        year_id = request.POST.get('academic_year', '').strip()
        degree_id = request.POST.get('degree', '').strip()
        course_number = request.POST.get('course_number', '').strip()
        if not year_id or not degree_id or not course_number:
            messages.error(request, 'Selecciona año académico, titulación y curso.')
        else:
            try:
                course_number_int = int(course_number)
            except ValueError:
                course_number_int = 0
            if course_number_int not in course_numbers:
                messages.error(request, 'Curso no válido.')
            else:
                course = Course.objects.filter(
                    academic_year_id=year_id,
                    degree_program_id=degree_id,
                    number=course_number_int,
                ).select_related('degree_program', 'academic_year').first()
                if not course:
                    messages.error(request, 'No existe ese curso para la titulación y año seleccionados.')
                else:
                    form_group_choices = _course_group_choices(course)
                    group_name = request.POST.get('group_name', '').strip()
                    if len(form_group_choices) > 1:
                        if not group_name or group_name not in form_group_choices:
                            messages.error(request, 'Selecciona tu especialidad o grupo.')
                        else:
                            _set_student_course(request, course)
                            _set_student_group(request, group_name)
                            messages.success(
                                request,
                                f'Horario configurado: {course.degree_program.code} · {course.number}º · {group_name}',
                            )
                            return redirect('horarios:student_my_schedule')
                    else:
                        _set_student_course(request, course)
                        _set_student_group(request, form_group_choices[0] if len(form_group_choices) == 1 else None)
                        messages.success(
                            request,
                            f'Horario configurado: {course.degree_program.code} · {course.number}º · {course.academic_year.name}',
                        )
                        return redirect('horarios:student_my_schedule')

    context = {
        'active_page': 'titulaciones',
        'degrees': degrees,
        'academic_years': AcademicYear.objects.order_by('-name'),
        'course_numbers': course_numbers,
        'current_year': current_year,
        'selected': selected,
        'selected_group': _get_student_group(request),
        'form_group_choices': form_group_choices,
        'user_role': role,
    }
    return render(request, 'horarios/student_schedule_setup.html', context)


@login_required
def student_my_schedule(request):
    role = _get_user_role(request)
    if role != 'STUD':
        return redirect('horarios:home')

    course = _get_student_course(request)
    if not course:
        return redirect('horarios:student_schedule_setup')

    schedule = _schedule_for_student(course)
    if not schedule:
        messages.warning(
            request,
            f'No hay horario publicado para {course.academic_year.name}. '
            'Cuando Decanato apruebe el horario podrás consultarlo aquí.',
        )
        return redirect('horarios:student_schedule_setup')

    return redirect(
        reverse('horarios:schedule_detail', kwargs={'pk': schedule.pk})
        + f'?degree={course.degree_program_id}&course={course.pk}'
    )


@login_required
def professor_my_schedule(request):
    role = _get_user_role(request)
    if role != 'PROF':
        return redirect('horarios:home')

    professor = Professor.objects.filter(email=request.user.email).first()
    if not professor:
        messages.warning(request, 'Tu usuario no está vinculado a ningún perfil de profesor.')
        return redirect('horarios:home')

    current_year = AcademicYear.objects.filter(is_current=True).first()
    schedule = _published_schedule(current_year)
    if not schedule:
        messages.warning(
            request,
            'No hay horario publicado para el año académico actual. '
            'Consulta más tarde o contacta con Decanato.',
        )
        return render(request, 'horarios/professor_my_schedule_empty.html', {
            'active_page': 'horarios',
            'user_role': role,
            'professor': professor,
            'current_year': current_year,
        })

    return redirect(
        reverse('horarios:schedule_detail', kwargs={'pk': schedule.pk})
        + f'?professor={professor.pk}'
    )


@login_required
def schedule_create(request):
    role = _get_user_role(request)
    if not _can_manage(role):
        messages.error(request, 'No tienes permisos para crear horarios.')
        return redirect('horarios:schedule_list')
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.status = 'DRAFT'
            schedule.save()
            _audit(request, 'schedule.create', f'{schedule.pk}:{schedule.name}')
            messages.success(request, f'Horario "{schedule.name}" creado como borrador.')
            return redirect('horarios:schedule_detail', pk=schedule.pk)
    else:
        form = ScheduleForm()
    return render(request, 'horarios/schedule_form.html', {'form': form, 'action': 'Crear', 'user_role': role})


@login_required
def schedule_update(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    role = _get_user_role(request)
    if role != 'DEAN':
        messages.error(request, 'Solo Decanato puede modificar este horario.')
        return redirect('horarios:schedule_list')
    if request.method == 'POST':
        form = ScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            _audit(request, 'schedule.update', f'{schedule.pk}:{schedule.name}')
            messages.success(request, 'Horario actualizado correctamente.')
            return redirect('horarios:schedule_list')
    else:
        form = ScheduleForm(instance=schedule)
    return render(request, 'horarios/schedule_form.html', {'form': form, 'action': 'Modificar', 'user_role': role})


@login_required
def schedule_delete(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    role = _get_user_role(request)
    if role != 'DEAN':
        messages.error(request, 'Solo Decanato puede eliminar este horario.')
        return redirect('horarios:schedule_list')
    if request.method == 'POST':
        detail = f'{schedule.pk}:{schedule.name}'
        schedule.delete()
        _audit(request, 'schedule.delete', detail)
        messages.success(request, 'Horario eliminado correctamente.')
        return redirect('horarios:schedule_list')
    return render(request, 'horarios/schedule_confirm_delete.html', {'schedule': schedule, 'user_role': role})


@login_required
def schedule_workflow(request, pk, action):
    schedule = get_object_or_404(Schedule, pk=pk)
    role = _get_user_role(request)
    transitions = {
        'submit': ('DRAFT', 'REVIEW', ['DEAN', 'IT']),
        'approve': ('REVIEW', 'APPROVED', ['DEAN']),
        'reject': ('REVIEW', 'REJECTED', ['DEAN']),
        'reopen': ('REJECTED', 'DRAFT', ['DEAN', 'IT']),
    }
    if action not in transitions:
        messages.error(request, 'Acción no válida.')
        return redirect('horarios:schedule_list')
    required_status, new_status, allowed_roles = transitions[action]
    if role not in allowed_roles:
        messages.error(request, 'No tienes permiso para esta acción.')
    elif schedule.status != required_status:
        messages.error(request, f'El horario no está en estado "{required_status}" para esta acción.')
    else:
        schedule.status = new_status
        schedule.save(update_fields=['status', 'updated_at'])
        _audit(request, f'schedule.workflow.{action}', f'{schedule.pk}:{required_status}->{new_status}')
        if action == 'submit':
            notify_schedule_submitted(schedule)
        elif action == 'approve':
            notify_schedule_approved(schedule)
        elif action == 'reject':
            notify_schedule_rejected(schedule)
        elif action == 'reopen':
            notify_schedule_reopened(schedule)
        labels = {'submit': 'enviado a revisión', 'approve': 'aprobado', 'reject': 'rechazado', 'reopen': 'reabierto como borrador'}
        messages.success(request, f'Horario "{schedule.name}" {labels[action]}.')
    return redirect('horarios:schedule_detail', pk=schedule.pk)


@login_required
def schedule_generate(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    role = _get_user_role(request)
    if not _can_manage(role) or schedule.status != 'DRAFT':
        messages.error(request, 'Solo Decanato o IT pueden generar horarios en estado borrador.')
        return redirect('horarios:schedule_detail', pk=schedule.pk)
    if request.method == 'POST':
        clear_existing = request.POST.get('clear_existing') == 'on'
        free_day = request.POST.get('free_day', '').strip() or None
        selected_degree = request.POST.get('degree', '').strip() or None
        selected_year = request.POST.get('academic_year', '').strip() or None
        selected_course_raw = request.POST.get('course', '').strip()

        if selected_year:
            year_obj = AcademicYear.objects.filter(pk=selected_year).first()
            if not year_obj:
                messages.error(request, 'Año académico no válido.')
                return redirect('horarios:schedule_detail', pk=schedule.pk)
            if year_obj.pk != schedule.academic_year_id:
                if not clear_existing and schedule.entries.exists():
                    messages.error(
                        request,
                        'Para cambiar de año académico activa "limpiar existente" o deja el mismo año del horario.'
                    )
                    return redirect('horarios:schedule_detail', pk=schedule.pk)
                schedule.academic_year = year_obj
                schedule.save(update_fields=['academic_year', 'updated_at'])

        selected_course_pk = None
        if selected_course_raw:
            course_scope = Course.objects.filter(pk=selected_course_raw, academic_year=schedule.academic_year).first()
            if not course_scope:
                messages.error(request, 'Curso no válido para el año académico del horario.')
                return redirect('horarios:schedule_detail', pk=schedule.pk)
            if selected_degree and str(course_scope.degree_program_id) != str(selected_degree):
                messages.error(request, 'El curso seleccionado no coincide con la titulación.')
                return redirect('horarios:schedule_detail', pk=schedule.pk)
            selected_course_pk = course_scope.pk

        selected_course_number = None
        if not selected_course_pk:
            course_number_raw = request.POST.get('course_number', '').strip()
            if course_number_raw:
                try:
                    selected_course_number = int(course_number_raw)
                except ValueError:
                    messages.error(request, 'Año de estudios no válido.')
                    return redirect('horarios:schedule_detail', pk=schedule.pk)
                if selected_course_number not in (1, 2, 3, 4, 5):
                    messages.error(request, 'Año de estudios no válido (debe ser 1, 2, 3, 4 o 5).')
                    return redirect('horarios:schedule_detail', pk=schedule.pk)

        result = generate_schedule_entries(
            schedule,
            clear_existing=clear_existing,
            free_day=free_day,
            degree_id=selected_degree,
            course_id=selected_course_pk,
            course_number=selected_course_number,
        )
        _audit(request, 'schedule.generate', json.dumps({'schedule': schedule.pk, **result}, default=str))
        created = result['created']
        total = result['total_offerings']
        unresolved = result['unresolved']
        if total == 0:
            other_years = AcademicYear.objects.filter(
                courses__subject_offerings__isnull=False,
            ).exclude(pk=schedule.academic_year_id).distinct()
            if other_years.exists():
                names = ', '.join(y.name for y in other_years)
                messages.warning(
                    request,
                    f'Este horario es del año {schedule.academic_year.name}, pero las ofertas importadas '
                    f'están en {names}. Vuelve a importar con: '
                    f'python manage.py import_horarios_excel --file ruta.xlsx --year {schedule.academic_year.name} '
                    f'--clear-eps --apply-schedule'
                )
            else:
                messages.warning(
                    request,
                    format_no_offerings_message(
                        schedule,
                        degree_id=selected_degree,
                        course_id=selected_course_pk,
                        course_number=selected_course_number,
                    ),
                )
        elif created == 0 and unresolved:
            messages.warning(
                request,
                f'No se pudo colocar ninguna sesión ({len(unresolved)} asignaturas sin hueco). '
                'Revisa franjas de tarde para 4º, disponibilidad de profesores o conflictos.'
            )
        elif unresolved:
            messages.warning(
                request,
                f'Se han creado {created} sesiones. Quedan {len(unresolved)} asignaturas con sesiones pendientes por restricciones.'
            )
        elif created == 0:
            messages.info(request, 'Todas las sesiones requeridas ya estaban programadas; no se añadió ninguna nueva.')
        else:
            scope = 'Horario generado correctamente'
            if selected_course_pk:
                scope = f'Horario generado para el curso seleccionado'
            elif selected_course_number:
                scope = f'Horario generado para {selected_course_number}º curso (todas las titulaciones)'
            elif selected_degree:
                deg = DegreeProgram.objects.filter(pk=selected_degree).first()
                scope = f'Horario generado para {deg.code if deg else "la titulación"}'
            messages.success(request, f'{scope}: {created} sesiones creadas sin conflictos.')
    return redirect('horarios:schedule_detail', pk=schedule.pk)


@login_required
def schedule_entry_create(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    role = _get_user_role(request)
    if not _can_manage(role) or schedule.status != 'DRAFT':
        messages.error(request, 'La edición manual solo está permitida en borrador para Decanato o IT.')
        return redirect('horarios:schedule_detail', pk=schedule.pk)
    conflict_errors = []
    suggested_slots = []

    if request.method == 'POST':
        form = ScheduleEntryForm(request.POST, schedule=schedule)
        if form.is_valid():
            offering = form.cleaned_data['subject_offering']
            slot = form.cleaned_data['timeslot']
            try:
                entry = create_schedule_entry(schedule, offering, slot)
                _audit(request, 'schedule.entry.create', f'{entry.pk}:{entry}')
                messages.success(request, 'Sesión añadida al horario sin conflictos.')
                return redirect('horarios:schedule_detail', pk=schedule.pk)
            except ValidationError as exc:
                conflict_errors = list(exc.messages)
                suggested_slots = suggest_slots_for_offering(schedule, offering, limit=6)
    elif request.method == 'GET' and request.GET.get('subject_offering') and request.GET.get('timeslot'):
        form = ScheduleEntryForm(request.GET, schedule=schedule)
        if form.is_valid():
            offering = form.cleaned_data['subject_offering']
            slot = form.cleaned_data['timeslot']
            conflict_errors = validate_schedule_entry(schedule, offering, slot)
            if conflict_errors:
                suggested_slots = suggest_slots_for_offering(schedule, offering, limit=6)
        else:
            form = ScheduleEntryForm(schedule=schedule)
    else:
        form = ScheduleEntryForm(schedule=schedule)
    return render(request, 'horarios/schedule_entry_form.html', {
        'form': form,
        'schedule': schedule,
        'action': 'Añadir sesión',
        'conflict_errors': conflict_errors,
        'suggested_slots': suggested_slots,
    })


@login_required
def schedule_entry_delete(request, pk, entry_pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    entry = get_object_or_404(ScheduleEntry, pk=entry_pk, schedule=schedule)
    role = _get_user_role(request)
    if not _can_manage(role) or schedule.status != 'DRAFT':
        messages.error(request, 'No tienes permisos para eliminar esta sesión.')
        return redirect('horarios:schedule_detail', pk=schedule.pk)
    if request.method == 'POST':
        detail = str(entry)
        entry.delete()
        _audit(request, 'schedule.entry.delete', detail)
        messages.success(request, 'Sesión eliminada correctamente.')
    return redirect('horarios:schedule_detail', pk=schedule.pk)


@login_required
def schedule_entry_move(request, pk, entry_pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    entry = get_object_or_404(
        ScheduleEntry.objects.select_related('timeslot', 'subject_offering', 'schedule__academic_year'),
        pk=entry_pk,
        schedule=schedule,
    )
    role = _get_user_role(request)
    if not _can_manage(role) or schedule.status != 'DRAFT':
        return JsonResponse({'ok': False, 'errors': ['No tienes permisos para mover esta sesión.']}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'errors': ['Método no permitido.']}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'errors': ['Formato de solicitud inválido.']}, status=400)

    day = (payload.get('day') or '').strip()
    start = (payload.get('start') or '').strip()
    end = (payload.get('end') or '').strip()
    if day not in dict(TimeSlotConfig.DAY_CHOICES):
        return JsonResponse({'ok': False, 'errors': ['Día de la semana inválido.']}, status=400)
    try:
        start_time = datetime.datetime.strptime(start, '%H:%M').time()
        end_time = datetime.datetime.strptime(end, '%H:%M').time()
    except ValueError:
        return JsonResponse({'ok': False, 'errors': ['Formato de hora inválido.']}, status=400)

    target_slot = TimeSlotConfig.objects.filter(
        academic_year=schedule.academic_year,
        day_of_week=day,
        start_time=start_time,
        end_time=end_time,
        is_active=True,
    ).first()
    if not target_slot:
        return JsonResponse({'ok': False, 'errors': ['No existe la franja objetivo.']}, status=404)

    entry.timeslot = target_slot
    try:
        entry.save()
    except ValidationError as exc:
        return JsonResponse({'ok': False, 'errors': list(exc.messages)}, status=400)

    _audit(
        request,
        'schedule.entry.move',
        json.dumps({'entry': entry.pk, 'day': day, 'start': start, 'end': end}, default=str),
    )
    return JsonResponse({'ok': True})


@login_required
def schedule_export_csv(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="horario_{schedule.pk}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Horario', schedule.name, schedule.academic_year.name, schedule.get_status_display()])
    writer.writerow(['Día', 'Inicio', 'Fin', 'Titulación', 'Curso', 'Asignatura', 'Profesor', 'Aula', 'Grupo'])
    for entry in schedule.entries.select_related('timeslot', 'subject_offering__subject', 'subject_offering__course__degree_program', 'subject_offering__professor', 'subject_offering__classroom').order_by('timeslot__day_of_week', 'timeslot__start_time'):
        writer.writerow([
            entry.timeslot.get_day_of_week_display(), entry.timeslot.start_time, entry.timeslot.end_time,
            entry.subject_offering.course.degree_program.code, entry.subject_offering.course.number,
            entry.subject_offering.subject.name, entry.subject_offering.professor,
            entry.subject_offering.classroom.code, entry.subject_offering.group_name,
        ])
    _audit(request, 'schedule.export.csv', str(schedule.pk))
    return response


@login_required
def schedule_export_excel(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    degree_id = request.GET.get('degree') or None
    course_id = request.GET.get('course') or None
    wb = build_schedule_workbook(schedule, degree_id=degree_id, course_id=course_id)
    safe_name = re.sub(r'[^\w\-]+', '_', schedule.name)[:40]
    filename = f'horario_{schedule.academic_year.name}_{safe_name}.xlsx'.replace(' ', '_')
    response = HttpResponse(
        workbook_to_bytes(wb),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    _audit(request, 'schedule.export.excel', str(schedule.pk))
    return response


@login_required
def schedule_api_json(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    data = {
        'id': schedule.pk,
        'name': schedule.name,
        'academic_year': schedule.academic_year.name,
        'status': schedule.status,
        'entries': [],
    }
    for entry in schedule.entries.select_related('timeslot', 'subject_offering__subject', 'subject_offering__course__degree_program', 'subject_offering__professor', 'subject_offering__classroom'):
        data['entries'].append({
            'day': entry.timeslot.get_day_of_week_display(),
            'start': entry.timeslot.start_time.strftime('%H:%M'),
            'end': entry.timeslot.end_time.strftime('%H:%M'),
            'degree': entry.subject_offering.course.degree_program.code,
            'course': entry.subject_offering.course.number,
            'subject': entry.subject_offering.subject.name,
            'subject_code': entry.subject_offering.subject.code,
            'teacher': str(entry.subject_offering.professor),
            'classroom': entry.subject_offering.classroom.code,
            'group': entry.subject_offering.group_name,
            'shared': entry.subject_offering.subject.is_shared,
        })
    return JsonResponse(data, json_dumps_params={'ensure_ascii': False})


@login_required
def reports(request):
    role = _get_user_role(request)
    schedule_id = request.GET.get('schedule')
    schedule = Schedule.objects.filter(pk=schedule_id).first() or Schedule.objects.order_by('-created_at').first()
    rows = get_generation_report(schedule) if schedule else []
    context = {
        'active_page': 'informes',
        'schedules': Schedule.objects.select_related('academic_year').all(),
        'schedule': schedule,
        'rows': rows,
        'ok_count': sum(1 for r in rows if r['ok']),
        'pending_count': sum(1 for r in rows if not r['ok']),
        'user_role': role,
    }
    return render(request, 'horarios/reports.html', context)


@login_required
def professor_availability(request):
    role = _get_user_role(request)
    if role not in ('PROF', 'DEAN', 'IT'):
        messages.error(request, 'Acceso no autorizado.')
        return redirect('horarios:home')
    professors = Professor.objects.all().order_by('last_name', 'first_name')
    selected_professor = None
    if role == 'PROF':
        selected_professor = Professor.objects.filter(email=request.user.email).first()
    else:
        prof_id = request.GET.get('professor')
        if prof_id:
            selected_professor = get_object_or_404(Professor, pk=prof_id)
    timeslots = []
    availabilities = []
    current_year = AcademicYear.objects.filter(is_current=True).first()
    if selected_professor and current_year:
        timeslots = [
            ts for ts in TimeSlotConfig.objects.filter(
                academic_year=current_year, is_active=True,
            ).order_by('day_of_week', 'start_time')
            if _is_allowed_slot_range(ts.start_time, ts.end_time)
        ]
        availabilities = selected_professor.availabilities.filter(
            timeslot__academic_year=current_year,
        ).select_related('timeslot')
    if request.method == 'POST' and selected_professor and current_year:
        form = ProfessorAvailabilityForm(
            request.POST, professor=selected_professor, academic_year=current_year,
        )
        if form.is_valid():
            form.save()
            _audit(request, 'professor.availability.update', str(selected_professor.pk))
            messages.success(request, 'Disponibilidad actualizada correctamente.')
            suffix = f'?professor={selected_professor.pk}' if role != 'PROF' else ''
            return redirect(request.path + suffix)
    else:
        form = (
            ProfessorAvailabilityForm(professor=selected_professor, academic_year=current_year)
            if selected_professor and current_year else None
        )
    availability_grid = _build_availability_grid(timeslots, form) if form and timeslots else None
    context = {
        'active_page': 'disponibilidad',
        'professors': professors,
        'selected_professor': selected_professor,
        'availabilities': availabilities,
        'timeslots': timeslots,
        'current_year': current_year,
        'availability_grid': availability_grid,
        'form': form,
        'user_role': role,
    }
    return render(request, 'horarios/professor_availability.html', context)


@login_required
def subject_offering_create(request):
    role = _get_user_role(request)
    if not _can_manage(role):
        messages.error(request, 'No tienes permisos para esta acción.')
        return redirect('horarios:dashboard')
    if request.method == 'POST':
        form = SubjectOfferingForm(request.POST)
        if form.is_valid():
            offering = form.save()
            _audit(request, 'subject_offering.create', str(offering.pk))
            messages.success(request, f'Oferta "{offering}" creada correctamente.')
            return redirect('horarios:degree_list')
    else:
        form = SubjectOfferingForm()
    return render(request, 'horarios/subject_offering_form.html', {
        'form': form,
        'action': 'Crear oferta de asignatura',
        'user_role': role,
        'active_page': 'ofertas',
    })


@login_required
def degree_list(request):
    role = _get_user_role(request)
    if role == 'STUD':
        return redirect('horarios:student_schedule_setup')
    q = request.GET.get('q', '')
    degrees = DegreeProgram.objects.filter(is_active=True).prefetch_related(
        'courses__subject_offerings__subject', 'courses__subject_offerings__professor',
    )
    if q:
        degrees = degrees.filter(Q(code__icontains=q) | Q(name__icontains=q))
    context = {
        'active_page': 'titulaciones',
        'degrees': degrees,
        'q': q,
        'user_role': _get_user_role(request),
    }
    return render(request, 'horarios/degree_list.html', context)


# =====================================================================
# V3 — Notificaciones y Configuración
# =====================================================================

from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def notifications_view(request):
    """Lista las notificaciones del usuario autenticado (RF-08, RF-10)."""
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'notifications': notifs,
        'active_page': 'notificaciones',
        'user_role': _get_user_role(request),
    }
    return render(request, 'horarios/notifications.html', context)


@login_required
def notification_toggle(request, pk):
    """Marca una notificación como leída/no leída."""
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.is_read = not n.is_read
    n.save(update_fields=['is_read', 'updated_at'])
    return redirect('horarios:notifications')


@login_required
@require_POST
def notification_mark_all(request):
    """Marca todas las notificaciones del usuario como leídas (POST)."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    if request.headers.get('Accept', '').startswith('application/json'):
        return JsonResponse({'ok': True})
    return redirect('horarios:notifications')


@login_required
def configuration_view(request):
    """Configuración de franjas horarias del año académico activo (RF-05)."""
    role = _get_user_role(request)
    if not _can_manage(role):
        messages.error(request, 'No tienes permisos para acceder a la configuración.')
        return redirect('horarios:home')

    current_year = AcademicYear.objects.filter(is_current=True).first()
    timeslots = []
    if current_year:
        timeslots = [
            ts for ts in TimeSlotConfig.objects.filter(academic_year=current_year).order_by('day_of_week', 'start_time')
            if _is_allowed_slot_range(ts.start_time, ts.end_time)
        ]

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add' and current_year:
            day = request.POST.get('day_of_week')
            start = request.POST.get('start_time')
            end = request.POST.get('end_time')
            try:
                start_time = datetime.datetime.strptime(start, '%H:%M').time()
                end_time = datetime.datetime.strptime(end, '%H:%M').time()
                if not _is_allowed_slot_range(start_time, end_time):
                    messages.error(request, 'Solo se permiten franjas 09:00-15:00 o 15:30-21:30.')
                    return redirect('horarios:configuration')
                TimeSlotConfig.objects.create(
                    academic_year=current_year,
                    day_of_week=day,
                    start_time=start_time,
                    end_time=end_time,
                    is_active=True,
                )
                _audit(request, 'timeslot.create', f'{day} {start}-{end}')
                messages.success(request, f'Franja {day} {start}-{end} añadida correctamente.')
            except Exception as e:
                messages.error(request, f'Error al crear franja: {e}')
        elif action == 'toggle':
            ts_id = request.POST.get('ts_id')
            ts = get_object_or_404(TimeSlotConfig, pk=ts_id)
            ts.is_active = not ts.is_active
            ts.save(update_fields=['is_active', 'updated_at'])
            _audit(request, 'timeslot.toggle', f'{ts.pk}:{ts.is_active}')
        elif action == 'delete':
            ts_id = request.POST.get('ts_id')
            ts = get_object_or_404(TimeSlotConfig, pk=ts_id)
            try:
                ts.delete()
                _audit(request, 'timeslot.delete', str(ts_id))
                messages.success(request, 'Franja eliminada.')
            except Exception as e:
                messages.error(request, f'No se pudo eliminar: {e}')
        return redirect('horarios:configuration')

    context = {
        'timeslots': timeslots,
        'current_year': current_year,
        'day_choices': TimeSlotConfig.DAY_CHOICES,
        'active_page': 'configuracion',
        'user_role': role,
    }
    return render(request, 'horarios/configuration.html', context)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class HorariosLoginView(LoginView):
    template_name = 'horarios/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        role = _get_user_role(self.request)
        if role == 'STUD':
            if _get_student_course(self.request):
                return reverse('horarios:student_my_schedule')
            return reverse('horarios:student_schedule_setup')
        if role == 'PROF':
            return reverse('horarios:professor_my_schedule')
        return self.get_redirect_url() or reverse('horarios:home')
