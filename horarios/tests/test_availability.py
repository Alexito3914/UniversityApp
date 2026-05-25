from datetime import time

from django.test import TestCase
from django.urls import reverse

from horarios.forms import ProfessorAvailabilityForm
from horarios.models import ProfessorAvailability, TimeSlotConfig

from .base import build_schedule_lab, create_user


class ProfessorAvailabilityFormTests(TestCase):
    def setUp(self):
        from horarios.models import AcademicYear, Professor
        self.year_a = AcademicYear.objects.create(name='2098-2099', is_current=False)
        self.year_b = AcademicYear.objects.create(name='2099-2100', is_current=True)
        self.professor = Professor.objects.create(
            first_name='Ana', last_name='García', email='ana.garcia@test.local',
        )
        for year in (self.year_a, self.year_b):
            TimeSlotConfig.objects.create(
                academic_year=year, day_of_week='FRI',
                start_time=time(9, 0), end_time=time(11, 0), is_active=True,
            )

    def test_availability_form_uses_current_year_only(self):
        form = ProfessorAvailabilityForm(professor=self.professor, academic_year=self.year_b)
        self.assertEqual(len(form.fields), 1)
        field_name = next(iter(form.fields))
        self.assertTrue(field_name.startswith('ts_'))
        ts_id = int(field_name.split('_')[1])
        self.assertEqual(TimeSlotConfig.objects.get(pk=ts_id).academic_year_id, self.year_b.pk)


class ProfessorAvailabilityViewTests(TestCase):
    def setUp(self):
        self.lab = build_schedule_lab()
        self.prof = create_user('prof_av', 'PROF', email=self.lab['prof_1'].email)
        self.dean = create_user('dean_av', 'DEAN')
        for day in ['MON', 'TUE', 'WED', 'THU', 'FRI']:
            TimeSlotConfig.objects.get_or_create(
                academic_year=self.lab['year'],
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(11, 0),
                defaults={'is_active': True},
            )

    def test_professor_view_renders_grid(self):
        self.client.login(username='prof_av', password='ucjc1234')
        response = self.client.get(reverse('horarios:professor_availability'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'av-glossary')
        self.assertIsNotNone(response.context['availability_grid'])
        self.assertEqual(len(response.context['form'].fields), len(response.context['timeslots']))

    def test_professor_can_save_preferred_slot(self):
        self.client.login(username='prof_av', password='ucjc1234')
        slot = self.lab['morning_slot']
        response = self.client.post(reverse('horarios:professor_availability'), {
            f'ts_{slot.pk}': 'PREFERRED',
        })
        self.assertRedirects(response, reverse('horarios:professor_availability'))
        self.assertTrue(
            ProfessorAvailability.objects.filter(
                professor=self.lab['prof_1'], timeslot=slot, status='PREFERRED',
            ).exists()
        )

    def test_dean_can_edit_other_professor(self):
        self.client.login(username='dean_av', password='ucjc1234')
        slot = self.lab['morning_slot']
        url = reverse('horarios:professor_availability') + f'?professor={self.lab["prof_2"].pk}'
        response = self.client.post(url, {f'ts_{slot.pk}': 'BLOCKED'})
        self.assertRedirects(response, url)
        self.assertTrue(
            ProfessorAvailability.objects.filter(
                professor=self.lab['prof_2'], timeslot=slot, status='BLOCKED',
            ).exists()
        )

    def test_student_cannot_access_availability(self):
        create_user('stud_av', 'STUD')
        self.client.login(username='stud_av', password='ucjc1234')
        response = self.client.get(reverse('horarios:professor_availability'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('horarios:home'))
