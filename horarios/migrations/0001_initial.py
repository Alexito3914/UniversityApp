# Generated manually for the V1 entregable.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AcademicYear',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=20, unique=True)),
                ('is_current', models.BooleanField(default=False)),
            ],
            options={'verbose_name': 'Año académico', 'verbose_name_plural': 'Años académicos'},
        ),
        migrations.CreateModel(
            name='Classroom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('name', models.CharField(max_length=80)),
                ('capacity', models.PositiveIntegerField(default=30)),
            ],
            options={'verbose_name': 'Aula', 'verbose_name_plural': 'Aulas'},
        ),
        migrations.CreateModel(
            name='DegreeProgram',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'verbose_name': 'Titulación', 'verbose_name_plural': 'Titulaciones'},
        ),
        migrations.CreateModel(
            name='Professor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('first_name', models.CharField(max_length=80)),
                ('last_name', models.CharField(max_length=120)),
                ('email', models.EmailField(max_length=254, unique=True)),
            ],
            options={'verbose_name': 'Profesor', 'verbose_name_plural': 'Profesores'},
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=120)),
                ('status', models.CharField(choices=[('DRAFT', 'Borrador'), ('REVIEW', 'Revisión'), ('APPROVED', 'Aprobado'), ('REJECTED', 'Rechazado')], default='DRAFT', max_length=10)),
                ('academic_year', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedules', to='horarios.academicyear')),
            ],
            options={'verbose_name': 'Horario', 'verbose_name_plural': 'Horarios'},
        ),
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('weekly_sessions', models.PositiveSmallIntegerField(default=2)),
                ('session_duration_hours', models.PositiveSmallIntegerField(default=2)),
                ('is_shared', models.BooleanField(default=False)),
                ('degree_programs', models.ManyToManyField(blank=True, related_name='shared_subjects', to='horarios.degreeprogram')),
            ],
            options={'verbose_name': 'Asignatura', 'verbose_name_plural': 'Asignaturas'},
        ),
        migrations.CreateModel(
            name='TimeSlotConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('day_of_week', models.CharField(choices=[('MON', 'Lunes'), ('TUE', 'Martes'), ('WED', 'Miércoles'), ('THU', 'Jueves'), ('FRI', 'Viernes')], max_length=3)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('academic_year', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timeslots', to='horarios.academicyear')),
            ],
            options={'verbose_name': 'Franja horaria', 'verbose_name_plural': 'Franjas horarias', 'ordering': ['day_of_week', 'start_time']},
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('role', models.CharField(choices=[('DEAN', 'Decanato'), ('PROF', 'Profesor'), ('STUD', 'Estudiante'), ('IT', 'IT'), ('CONS', 'Consultor')], max_length=10)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('number', models.PositiveSmallIntegerField()),
                ('shift', models.CharField(choices=[('MORNING', 'Mañana'), ('AFTERNOON', 'Tarde')], default='MORNING', max_length=20)),
                ('academic_year', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='courses', to='horarios.academicyear')),
                ('degree_program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='courses', to='horarios.degreeprogram')),
            ],
            options={'verbose_name': 'Curso', 'verbose_name_plural': 'Cursos', 'unique_together': {('degree_program', 'academic_year', 'number')}},
        ),
        migrations.CreateModel(
            name='ProfessorAvailability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('PREFERRED', 'Disponibilidad preferente'), ('BLOCKED', 'Indisponibilidad')], max_length=10)),
                ('professor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='availabilities', to='horarios.professor')),
                ('timeslot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='professor_availabilities', to='horarios.timeslotconfig')),
            ],
            options={'verbose_name': 'Disponibilidad del profesor', 'verbose_name_plural': 'Disponibilidades del profesorado', 'unique_together': {('professor', 'timeslot')}},
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('first_name', models.CharField(max_length=80)),
                ('last_name', models.CharField(max_length=120)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='students', to='horarios.course')),
            ],
            options={'verbose_name': 'Estudiante', 'verbose_name_plural': 'Estudiantes'},
        ),
        migrations.CreateModel(
            name='SubjectOffering',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('group_name', models.CharField(default='Grupo A', max_length=50)),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subject_offerings', to='horarios.classroom')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subject_offerings', to='horarios.course')),
                ('professor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subject_offerings', to='horarios.professor')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offerings', to='horarios.subject')),
            ],
            options={'verbose_name': 'Oferta de asignatura', 'verbose_name_plural': 'Ofertas de asignaturas', 'unique_together': {('subject', 'course', 'group_name')}},
        ),
        migrations.CreateModel(
            name='ScheduleEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='horarios.schedule')),
                ('subject_offering', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedule_entries', to='horarios.subjectoffering')),
                ('timeslot', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='schedule_entries', to='horarios.timeslotconfig')),
            ],
            options={'verbose_name': 'Entrada de horario', 'verbose_name_plural': 'Entradas de horario'},
        ),
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrollments', to='horarios.student')),
                ('subject_offering', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrollments', to='horarios.subjectoffering')),
            ],
            options={'verbose_name': 'Matrícula', 'verbose_name_plural': 'Matrículas', 'unique_together': {('student', 'subject_offering')}},
        ),
        migrations.AddConstraint(
            model_name='scheduleentry',
            constraint=models.UniqueConstraint(fields=('schedule', 'subject_offering', 'timeslot'), name='unique_schedule_offering_timeslot'),
        ),
        migrations.AddConstraint(
            model_name='scheduleentry',
            constraint=models.UniqueConstraint(fields=('schedule', 'timeslot', 'subject_offering'), name='unique_schedule_slot_subject'),
        ),
    ]
