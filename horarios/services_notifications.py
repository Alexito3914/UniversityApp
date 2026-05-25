"""Notificaciones in-app ligadas a eventos del sistema."""
from django.contrib.auth.models import User

from .models import Notification, Schedule, UserProfile


def _users_with_role(role):
    return User.objects.filter(userprofile__role=role)


def _users_for_professors_in_schedule(schedule):
    emails = schedule.entries.values_list(
        'subject_offering__professor__email', flat=True,
    ).distinct()
    return User.objects.filter(email__in=emails)


def notify_users(users, message, notif_type='info'):
    for user in users.distinct():
        Notification.objects.create(user=user, message=message, notif_type=notif_type)


def notify_role(role, message, notif_type='info'):
    notify_users(_users_with_role(role), message, notif_type)


def notify_schedule_submitted(schedule):
    notify_role(
        'DEAN',
        f'El horario «{schedule.name}» ({schedule.academic_year.name}) está pendiente de aprobación.',
        'warn',
    )


def notify_schedule_approved(schedule):
    notify_role(
        'IT',
        f'Horario «{schedule.name}» aprobado y publicado para {schedule.academic_year.name}.',
        'ok',
    )
    notify_users(
        _users_for_professors_in_schedule(schedule),
        f'Tu horario «{schedule.name}» ya está publicado. Consulta «Mi horario».',
        'ok',
    )


def notify_schedule_rejected(schedule):
    notify_role(
        'IT',
        f'El horario «{schedule.name}» ha sido rechazado. Revisa y reenvía a aprobación.',
        'err',
    )


def notify_schedule_reopened(schedule):
    notify_role(
        'IT',
        f'El horario «{schedule.name}» se ha reabierto como borrador.',
        'info',
    )
