"""
Formularios del sistema de gestión de horarios UCJC.
Implementan validación de restricciones de dominio (RF-02, RD-05, RD-12).
"""

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import (
    AcademicYear, Course, DegreeProgram, Professor, Schedule, Subject,
    SubjectOffering, ProfessorAvailability,
    TimeSlotConfig, ScheduleEntry,
)
from .catalog import provision_courses_for_degree
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


class ExcelImportForm(forms.Form):
    """Subida de Excel del decanato (Listado o Listado 4 grados)."""

    excel_file = forms.FileField(
        label='Archivo Excel (.xlsx)',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.xlsx'}),
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        label='Año académico',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    clear_eps = forms.BooleanField(
        required=False,
        initial=True,
        label='Reemplazar ofertas EPS existentes (INF, ROB, TEL, Doble Grado)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    auto_generate = forms.BooleanField(
        required=False,
        initial=True,
        label='Generar horarios 1º y 2º cuatrimestre automáticamente',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = AcademicYear.objects.filter(is_current=True).first()
        if current:
            self.fields['academic_year'].initial = current.pk

    def clean_excel_file(self):
        uploaded = self.cleaned_data['excel_file']
        if not uploaded.name.lower().endswith('.xlsx'):
            raise ValidationError('Solo se admiten archivos .xlsx')
        if uploaded.size > 15 * 1024 * 1024:
            raise ValidationError('El archivo no puede superar 15 MB.')
        return uploaded


class DegreeProgramForm(forms.ModelForm):
    """Alta/edición de titulación por Decanato."""

    provision_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        required=False,
        label='Año académico para crear cursos',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Al crear la titulación se generan los cursos (1º–4º) en este año.',
    )

    class Meta:
        model = DegreeProgram
        fields = ['code', 'name', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: INF, ROB, TEL'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo del grado'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'code': 'Código',
            'name': 'Nombre de la titulación',
            'is_active': 'Activa',
        }

    def __init__(self, *args, is_create=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_create = is_create
        current = AcademicYear.objects.filter(is_current=True).first()
        if current:
            self.fields['provision_year'].initial = current.pk
        if not is_create:
            self.fields['provision_year'].widget = forms.HiddenInput()
            self.fields['provision_year'].required = False

    def save(self, commit=True):
        degree = super().save(commit=commit)
        if commit and self.is_create:
            year = self.cleaned_data.get('provision_year')
            provision_courses_for_degree(degree, year)
        return degree


class SubjectForm(forms.ModelForm):
    """Alta/edición de asignatura vinculada a una o más titulaciones."""

    class Meta:
        model = Subject
        fields = ['code', 'name', 'weekly_sessions', 'is_shared', 'degree_programs']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 76001'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'weekly_sessions': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'is_shared': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'degree_programs': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
        }
        labels = {
            'code': 'Código de asignatura',
            'name': 'Nombre',
            'weekly_sessions': 'Sesiones semanales (2 h cada una)',
            'is_shared': 'Asignatura transversal',
            'degree_programs': 'Titulaciones',
        }

    def __init__(self, *args, degree=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['degree_programs'].queryset = DegreeProgram.objects.filter(is_active=True)
        if degree:
            self.fields['degree_programs'].initial = [degree.pk]


class SubjectOfferingForm(forms.ModelForm):
    """Formulario para crear/editar una oferta docente."""

    class Meta:
        model = SubjectOffering
        fields = [
            'subject', 'course', 'professor', 'classroom',
            'group_name', 'semester', 'weekly_sessions',
        ]
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'professor': forms.Select(attrs={'class': 'form-select'}),
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'group_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Grupo A / Laboratorio'}),
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'weekly_sessions': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
        }
        labels = {
            'subject': 'Asignatura',
            'course': 'Curso',
            'professor': 'Profesor responsable',
            'classroom': 'Aula asignada',
            'group_name': 'Nombre del grupo',
            'semester': 'Cuatrimestre',
            'weekly_sessions': 'Sesiones por semana',
        }

    def __init__(self, *args, degree=None, **kwargs):
        super().__init__(*args, **kwargs)
        current = AcademicYear.objects.filter(is_current=True).first()
        course_qs = Course.objects.select_related('degree_program', 'academic_year')
        if current:
            course_qs = course_qs.filter(academic_year=current)
        if degree:
            course_qs = course_qs.filter(degree_program=degree)
            self.fields['subject'].queryset = Subject.objects.filter(
                Q(degree_programs=degree) | Q(offerings__course__degree_program=degree)
            ).distinct()
        self.fields['course'].queryset = course_qs.order_by('degree_program__code', 'number')


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
