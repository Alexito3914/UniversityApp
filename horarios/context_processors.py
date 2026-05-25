"""Context processor: inyecta datos de la barra/sidebar en cada request."""
import json
from django.utils.timesince import timesince
from .models import AcademicYear, DegreeProgram, Schedule, Notification, UserProfile


def navigation(request):
    if not request.user.is_authenticated:
        return {}

    notif_qs = Notification.objects.filter(user=request.user)[:20]
    notifs_payload = [{
        'id': n.pk,
        'msg': n.message,
        'type': n.notif_type,
        'when': f'hace {timesince(n.created_at)}'.split(',')[0],
        'read': n.is_read,
    } for n in notif_qs]

    try:
        user_role = request.user.userprofile.role
        role_label = request.user.userprofile.get_role_display()
    except UserProfile.DoesNotExist:
        user_role = None
        role_label = 'Usuario'

    full_name = request.user.get_full_name().strip() or request.user.username
    name_parts = full_name.split()
    user_initials = ''.join(p[0] for p in name_parts[:2]).upper()[:2] or request.user.username[:2].upper()

    return {
        'unread_notifications': Notification.objects.filter(user=request.user, is_read=False).count(),
        'notifications_json': json.dumps(notifs_payload, ensure_ascii=False),
        'current_year': AcademicYear.objects.filter(is_current=True).first(),
        'total_titulaciones': DegreeProgram.objects.filter(is_active=True).count(),
        'total_horarios': Schedule.objects.count(),
        'horarios_review': Schedule.objects.filter(status='REVIEW').count(),
        'horarios_draft': Schedule.objects.filter(status='DRAFT').count(),
        'horarios_approved': Schedule.objects.filter(status='APPROVED').count(),
        'user_role': user_role,
        'role_label': role_label,
        'user_display_name': full_name,
        'user_initials': user_initials,
    }
