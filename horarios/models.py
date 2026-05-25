from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserProfile(BaseModel):
    ROLE_CHOICES = [
        ('DEAN', 'Decanato'),
        ('PROF', 'Profesor'),
        ('STUD', 'Estudiante'),
        ('IT', 'IT'),
        ('CONS', 'Consultor'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class DegreeProgram(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Titulación'
        verbose_name_plural = 'Titulaciones'

    def __str__(self):
        return self.name


class AcademicYear(BaseModel):
    name = models.CharField(max_length=20, unique=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Año académico'
        verbose_name_plural = 'Años académicos'

    def __str__(self):
        return self.name


class Course(BaseModel):
    SHIFT_CHOICES = [
        ('MORNING', 'Mañana'),
        ('AFTERNOON', 'Tarde'),
    ]

    degree_program = models.ForeignKey(DegreeProgram, on_delete=models.CASCADE, related_name='courses')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='courses')
    number = models.PositiveSmallIntegerField()
    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES, default='MORNING')

    class Meta:
        unique_together = ('degree_program', 'academic_year', 'number')
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'

    def __str__(self):
        return f"{self.degree_program.code} - {self.number}º ({self.academic_year.name})"


class Professor(BaseModel):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=160, blank=True, help_text='Nombre tal como figura en el Excel')

    class Meta:
        verbose_name = 'Profesor'
        verbose_name_plural = 'Profesores'

    def __str__(self):
        if self.display_name:
            return self.display_name
        return f"{self.first_name} {self.last_name}"


class Student(BaseModel):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='students')

    class Meta:
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Classroom(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=80)
    capacity = models.PositiveIntegerField(default=30)

    class Meta:
        verbose_name = 'Aula'
        verbose_name_plural = 'Aulas'

    def __str__(self):
        return self.code


class TimeSlotConfig(BaseModel):
    DAY_CHOICES = [
        ('MON', 'Lunes'),
        ('TUE', 'Martes'),
        ('WED', 'Miércoles'),
        ('THU', 'Jueves'),
        ('FRI', 'Viernes'),
    ]

    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='timeslots')
    day_of_week = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Franja horaria'
        verbose_name_plural = 'Franjas horarias'
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class Subject(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    weekly_sessions = models.PositiveSmallIntegerField(default=2)
    session_duration_hours = models.PositiveSmallIntegerField(default=2)
    is_shared = models.BooleanField(default=False)
    degree_programs = models.ManyToManyField(DegreeProgram, related_name='shared_subjects', blank=True)

    class Meta:
        verbose_name = 'Asignatura'
        verbose_name_plural = 'Asignaturas'

    def __str__(self):
        return f"{self.code} - {self.name}"


class SubjectOffering(BaseModel):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='offerings')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subject_offerings')
    professor = models.ForeignKey(Professor, on_delete=models.PROTECT, related_name='subject_offerings')
    classroom = models.ForeignKey(Classroom, on_delete=models.PROTECT, related_name='subject_offerings')
    group_name = models.CharField(max_length=50, default='Grupo A')

    class Meta:
        unique_together = ('subject', 'course', 'group_name')
        verbose_name = 'Oferta de asignatura'
        verbose_name_plural = 'Ofertas de asignaturas'

    def __str__(self):
        return f"{self.subject.code} - {self.course} - {self.group_name}"


class ProfessorAvailability(BaseModel):
    STATUS_CHOICES = [
        ('PREFERRED', 'Disponibilidad preferente'),
        ('BLOCKED', 'Indisponibilidad'),
    ]

    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name='availabilities')
    timeslot = models.ForeignKey(TimeSlotConfig, on_delete=models.CASCADE, related_name='professor_availabilities')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ('professor', 'timeslot')
        verbose_name = 'Disponibilidad del profesor'
        verbose_name_plural = 'Disponibilidades del profesorado'

    def __str__(self):
        return f"{self.professor} - {self.timeslot} - {self.get_status_display()}"


class Schedule(BaseModel):
    STATUS_CHOICES = [
        ('DRAFT', 'Borrador'),
        ('REVIEW', 'Revisión'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado'),
    ]

    name = models.CharField(max_length=120)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='schedules')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')

    class Meta:
        verbose_name = 'Horario'
        verbose_name_plural = 'Horarios'

    def __str__(self):
        return f"{self.name} - {self.academic_year.name}"


class ScheduleEntry(BaseModel):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='entries')
    subject_offering = models.ForeignKey(SubjectOffering, on_delete=models.CASCADE, related_name='schedule_entries')
    timeslot = models.ForeignKey(TimeSlotConfig, on_delete=models.PROTECT, related_name='schedule_entries')

    class Meta:
        verbose_name = 'Entrada de horario'
        verbose_name_plural = 'Entradas de horario'
        constraints = [
            models.UniqueConstraint(fields=['schedule', 'subject_offering', 'timeslot'], name='unique_schedule_offering_timeslot'),
            models.UniqueConstraint(fields=['schedule', 'timeslot', 'subject_offering'], name='unique_schedule_slot_subject'),
        ]

    def __str__(self):
        return f"{self.subject_offering} - {self.timeslot}"

    def clean(self):
        super().clean()
        if not self.schedule_id or not self.subject_offering_id or not self.timeslot_id:
            return
        from .services import validate_schedule_entry
        errors = validate_schedule_entry(
            self.schedule,
            self.subject_offering,
            self.timeslot,
            exclude_pk=self.pk,
        )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Notification(BaseModel):
    """Notificación in-app del sistema (RF-08, RF-10)."""
    TYPE_CHOICES = [
        ('ok', 'Éxito'),
        ('warn', 'Aviso'),
        ('err', 'Error'),
        ('info', 'Información'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    notif_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='info')
    is_read = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notif_type}] {self.message[:40]}"


class Enrollment(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    subject_offering = models.ForeignKey(SubjectOffering, on_delete=models.CASCADE, related_name='enrollments')

    class Meta:
        unique_together = ('student', 'subject_offering')
        verbose_name = 'Matrícula'
        verbose_name_plural = 'Matrículas'

    def __str__(self):
        return f"{self.student} - {self.subject_offering}"
