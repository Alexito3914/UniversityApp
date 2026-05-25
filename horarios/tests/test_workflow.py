from django.test import TestCase
from django.urls import reverse

from horarios.models import Schedule

from .base import build_schedule_lab, create_user


class ScheduleWorkflowTests(TestCase):
    def setUp(self):
        self.lab = build_schedule_lab()
        self.schedule = self.lab['schedule']
        self.dean = create_user('dean_wf', 'DEAN')
        self.it = create_user('it_wf', 'IT')
        self.prof = create_user('prof_wf', 'PROF', email=self.lab['prof_1'].email)

    def _workflow(self, user, action):
        self.client.login(username=user, password='ucjc1234')
        return self.client.get(reverse('horarios:schedule_workflow', kwargs={'pk': self.schedule.pk, 'action': action}))

    def test_submit_draft_to_review(self):
        response = self._workflow('it_wf', 'submit')
        self.assertRedirects(response, reverse('horarios:schedule_detail', kwargs={'pk': self.schedule.pk}))
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.status, 'REVIEW')

    def test_approve_review_to_approved(self):
        self.schedule.status = 'REVIEW'
        self.schedule.save(update_fields=['status'])
        self._workflow('dean_wf', 'approve')
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.status, 'APPROVED')

    def test_reject_review_to_rejected(self):
        self.schedule.status = 'REVIEW'
        self.schedule.save(update_fields=['status'])
        self._workflow('dean_wf', 'reject')
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.status, 'REJECTED')

    def test_reopen_rejected_to_draft(self):
        self.schedule.status = 'REJECTED'
        self.schedule.save(update_fields=['status'])
        self._workflow('dean_wf', 'reopen')
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.status, 'DRAFT')

    def test_professor_cannot_submit(self):
        response = self._workflow('prof_wf', 'submit')
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.status, 'DRAFT')
        self.assertEqual(response.status_code, 302)

    def test_it_cannot_approve(self):
        self.schedule.status = 'REVIEW'
        self.schedule.save(update_fields=['status'])
        self._workflow('it_wf', 'approve')
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.status, 'REVIEW')

    def test_approve_fails_if_not_in_review(self):
        self._workflow('dean_wf', 'approve')
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.status, 'DRAFT')

    def test_invalid_action_redirects_to_list(self):
        self.client.login(username='dean_wf', password='ucjc1234')
        response = self.client.get(reverse('horarios:schedule_workflow', kwargs={'pk': self.schedule.pk, 'action': 'invalid'}))
        self.assertRedirects(response, reverse('horarios:schedule_list'))
