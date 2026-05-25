from django.test import TestCase
from django.urls import reverse

from horarios.models import Notification, Schedule

from .base import add_schedule_entry, build_schedule_lab, create_user


class ProfessorMyScheduleTests(TestCase):
    def setUp(self):
        self.lab = build_schedule_lab()
        self.schedule = self.lab['schedule']
        self.schedule.status = 'APPROVED'
        self.schedule.save(update_fields=['status'])
        create_user('prof_ms', 'PROF', email=self.lab['prof_1'].email)
        add_schedule_entry(self.schedule, self.lab['offering_a'], self.lab['morning_slot'])

    def test_professor_my_schedule_opens_published_detail(self):
        self.client.login(username='prof_ms', password='ucjc1234')
        response = self.client.get(reverse('horarios:professor_my_schedule'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/horarios/{self.schedule.pk}/', response.url)
        self.assertIn(f'professor={self.lab["prof_1"].pk}', response.url)

    def test_professor_schedule_list_redirects(self):
        self.client.login(username='prof_ms', password='ucjc1234')
        response = self.client.get(reverse('horarios:schedule_list'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('horarios:professor_my_schedule'))

    def test_professor_sees_empty_page_without_published_schedule(self):
        self.schedule.status = 'DRAFT'
        self.schedule.save(update_fields=['status'])
        self.client.login(username='prof_ms', password='ucjc1234')
        response = self.client.get(reverse('horarios:professor_my_schedule'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay ningún horario')


class WorkflowNotificationTests(TestCase):
    def setUp(self):
        self.lab = build_schedule_lab()
        self.schedule = self.lab['schedule']
        create_user('dean_nf', 'DEAN')
        create_user('it_nf', 'IT')

    def test_submit_notifies_dean(self):
        self.client.login(username='it_nf', password='ucjc1234')
        self.client.get(reverse('horarios:schedule_workflow', kwargs={'pk': self.schedule.pk, 'action': 'submit'}))
        self.assertTrue(
            Notification.objects.filter(user__username='dean_nf', message__icontains='pendiente').exists()
        )

    def test_approve_notifies_it(self):
        self.schedule.status = 'REVIEW'
        self.schedule.save(update_fields=['status'])
        self.client.login(username='dean_nf', password='ucjc1234')
        self.client.get(reverse('horarios:schedule_workflow', kwargs={'pk': self.schedule.pk, 'action': 'approve'}))
        self.assertTrue(
            Notification.objects.filter(user__username='it_nf', message__icontains='aprobado').exists()
        )
