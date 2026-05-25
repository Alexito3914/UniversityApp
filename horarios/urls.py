from django.urls import path
from . import views

app_name = 'horarios'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('titulaciones/', views.degree_list, name='degree_list'),
    path('informes/', views.reports, name='reports'),
    path('horarios/', views.schedule_list, name='schedule_list'),
    path('mi-horario/', views.student_my_schedule, name='student_my_schedule'),
    path('mi-horario/configurar/', views.student_schedule_setup, name='student_schedule_setup'),
    path('mi-horario-profesor/', views.professor_my_schedule, name='professor_my_schedule'),
    path('horarios/nuevo/', views.schedule_create, name='schedule_create'),
    path('horarios/<int:pk>/editar/', views.schedule_update, name='schedule_update'),
    path('horarios/<int:pk>/eliminar/', views.schedule_delete, name='schedule_delete'),
    path('horarios/<int:pk>/', views.schedule_detail, name='schedule_detail'),
    path('horarios/<int:pk>/generar/', views.schedule_generate, name='schedule_generate'),
    path('horarios/<int:pk>/sesiones/nueva/', views.schedule_entry_create, name='schedule_entry_create'),
    path('horarios/<int:pk>/sesiones/<int:entry_pk>/eliminar/', views.schedule_entry_delete, name='schedule_entry_delete'),
    path('horarios/<int:pk>/sesiones/<int:entry_pk>/mover/', views.schedule_entry_move, name='schedule_entry_move'),
    path('horarios/<int:pk>/workflow/<str:action>/', views.schedule_workflow, name='schedule_workflow'),
    path('horarios/<int:pk>/exportar/csv/', views.schedule_export_csv, name='schedule_export_csv'),
    path('api/horarios/<int:pk>.json', views.schedule_api_json, name='schedule_api_json'),
    path('disponibilidad/', views.professor_availability, name='professor_availability'),
    path('ofertas/nueva/', views.subject_offering_create, name='subject_offering_create'),
    path('notificaciones/', views.notifications_view, name='notifications'),
    path('notificaciones/<int:pk>/toggle/', views.notification_toggle, name='notification_toggle'),
    path('notificaciones/marcar-todas/', views.notification_mark_all, name='notification_mark_all'),
    path('configuracion/', views.configuration_view, name='configuration'),
]
