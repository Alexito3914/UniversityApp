"""
Formularios del sistema de gestión de horarios UCJC.
Implementan validación de restricciones de dominio (RF-02, RD-05, RD-12).
"""

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import (
    Schedule, SubjectOffering, ProfessorAvailability,
    TimeSlotConfig, ScheduleEntry
)
from .services import AFTERNOON_END, AFTERNOON_START, MORNING_END, MORNING_START, validate_schedule_entry


class ScheduleForm(forms.ModelForm):
    """Formulario para crear/editar un horario académico (RF-01)."""

    class Meta:
        model = Schedule
        fields = ['name', 'academic_year', 'semester']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Horario 2026-27 Primer Semestre'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'semester': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'name': 'Nombre del horario',
            'academic_year': 'Año académico',
            'semester': 'Cuatrimestre',
        }


class SubjectOfferingForm(forms.ModelForm):
    """Formulario para crear una oferta de asignatura."""

    class Meta:
        model = SubjectOffering
        fields = ['subject', 'course', 'professor', 'classroom', 'group_name']
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'professor': forms.Select(attrs={'class': 'form-select'}),
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'group_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Grupo A / Laboratorio'}),
        }
        labels = {
            'subject': 'Asignatura',
            'course': 'Curso',
            'professor': 'Profesor responsable',
            'classroom': 'Aula asignada',
            'group_name': 'Nombre del grupo',
        }


class ScheduleEntryForm(forms.ModelForm):
    """Formulario de edición manual de entradas del horario (RF-07)."""

    class Meta:
        model = ScheduleEntry
        fields = ['subject_offering', 'timeslot']
        widgets = {
            'subject_offering': forms.Select(attrs={'class': 'form-select'}),
            'timeslot': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'subject_offering': 'Asignatura / grupo',
            'timeslot': 'Franja horaria',
        }

    def __init__(self, *args, schedule=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.schedule = schedule
        if schedule:
            self.fields['subject_offering'].queryset = SubjectOffering.objects.filter(
                course__academic_year=schedule.academic_year,
                semester=schedule.semester,
            ).select_related('subject', 'course__degree_program', 'professor', 'classroom')
            self.fields['timeslot'].queryset = TimeSlotConfig.objects.filter(
                academic_year=schedule.academic_year, is_active=True
            ).filter(
                Q(start_time__gte=MORNING_START, end_time__lte=MORNING_END) |
                Q(start_time__gte=AFTERNOON_START, end_time__lte=AFTERNOON_END)
            ).order_by('day_of_week', 'start_time')

    def clean(self):
        cleaned = super().clean()
        offering = cleaned.get('subject_offering')
        slot = cleaned.get('timeslot')
        if self.schedule and offering and slot:
            errors = validate_schedule_entry(
                self.schedule,
                offering,
                slot,
                exclude_pk=self.instance.pk if self.instance else None,
            )
            if errors:
                raise ValidationError(errors)
        return cleaned


class ProfessorAvailabilityForm(forms.Form):
    """Formulario para que el profesorado registre su disponibilidad (RF-08)."""
    STATUS_CHOICES = [
        ('', '— Sin definir —'),
        ('PREFERRED', 'Disponibilidad preferente'),
        ('BLOCKED', 'Indisponibilidad'),
    ]

    def __init__(self, *args, professor=None, academic_year=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.professor = professor
        if professor and academic_year:
            timeslots = TimeSlotConfig.objects.filter(
                academic_year=academic_year, is_active=True,
            ).filter(
                Q(start_time__gte=MORNING_START, end_time__lte=MORNING_END) |
                Q(start_time__gte=AFTERNOON_START, end_time__lte=AFTERNOON_END)
            ).order_by('day_of_week', 'start_time')
            existing = {a.timeslot_id: a.status for a in professor.availabilities.all()}
            for ts in timeslots:
                field_name = f'ts_{ts.pk}'
                self.fields[field_name] = forms.ChoiceField(
                    choices=self.STATUS_CHOICES,
                    required=False,
                    initial=existing.get(ts.pk, ''),
                    label=str(ts),
                    widget=forms.HiddenInput(attrs={'class': 'av-state-input'}),
                )

    def save(self):
        """Guarda o elimina las disponibilidades según la selección del formulario."""
        if not self.professor:
            return
        for field_name, value in self.cleaned_data.items():
            if not field_name.startswith('ts_'):
                continue
            ts_id = int(field_name.split('_')[1])
            ts = TimeSlotConfig.objects.get(pk=ts_id)
            if value:
                ProfessorAvailability.objects.update_or_create(
                    professor=self.professor,
                    timeslot=ts,
                    defaults={'status': value},
                )
            else:
                ProfessorAvailability.objects.filter(professor=self.professor, timeslot=ts).delete()
