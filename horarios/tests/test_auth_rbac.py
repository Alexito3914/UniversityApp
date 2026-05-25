import json

from django.test import TestCase
from django.urls import reverse

from horarios.models import ProfessorAvailability, Schedule

from .base import add_schedule_entry, build_schedule_lab, create_user


class AuthAndRBACTests(TestCase):
    def setUp(self):
        self.lab = build_schedule_lab()
        self.dean = create_user('dean_test', 'DEAN')
        self.it = create_user('it_test', 'IT')
        self.prof = create_user('prof_test', 'PROF', email=self.lab['prof_1'].email)
        self.student = create_user('student_test', 'STUD')

    def test_login_redirects_student_to_setup(self):
        response = self.client.post(reverse('login'), {
            'username': 'student_test',
            'password': 'ucjc1234',
        })
        self.assertRedirects(response, reverse('horarios:student_schedule_setup'))

    def test_login_redirects_dean_to_home(self):
        response = self.client.post(reverse('login'), {
            'username': 'dean_test',
            'password': 'ucjc1234',
        })
        self.assertRedirects(response, reverse('horarios:home'))

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': 'dean_test',
            'password': 'wrong',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Credenciales incorrectas')

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse('horarios:home'))
        self.assertRedirects(response, f"{reverse('login')}?next=/")

    def test_student_cannot_access_schedule_list(self):
        self.client.login(username='student_test', password='ucjc1234')
        response = self.client.get(reverse('horarios:schedule_list'))
        self.assertRedirects(response, reverse('horarios:student_schedule_setup'))

    def _assert_redirects_to(self, response, url):
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], url)

    def test_student_cannot_access_configuration(self):
        self.client.login(username='student_test', password='ucjc1234')
        response = self.client.get(reverse('horarios:configuration'))
        self._assert_redirects_to(response, reverse('horarios:home'))

    def test_professor_cannot_generate_schedule(self):
        self.client.login(username='prof_test', password='ucjc1234')
        response = self.client.post(reverse('horarios:schedule_generate', kwargs={'pk': self.lab['schedule'].pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            reverse('horarios:schedule_detail', kwargs={'pk': self.lab['schedule'].pk}),
        )

    def test_professor_can_open_availability(self):
        self.client.login(username='prof_test', password='ucjc1234')
        response = self.client.get(reverse('horarios:professor_availability'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'av-glossary')

    def test_dean_can_open_configuration(self):
        self.client.login(username='dean_test', password='ucjc1234')
        response = self.client.get(reverse('horarios:configuration'))
        self.assertEqual(response.status_code, 200)

    def test_it_can_create_schedule(self):
        self.client.login(username='it_test', password='ucjc1234')
        response = self.client.post(reverse('horarios:schedule_create'), {
            'name': 'Horario IT nuevo',
            'academic_year': self.lab['year'].pk,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Schedule.objects.filter(name='Horario IT nuevo', status='DRAFT').exists())
