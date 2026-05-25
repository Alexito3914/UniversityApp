from django.test import TestCase
from django.urls import reverse

from horarios.models import Course, DegreeProgram, Subject

from .base import create_user


class CatalogManagementTests(TestCase):
    def setUp(self):
        self.dean = create_user('dean_cat', 'DEAN')
        self.lab_year = None
        from horarios.models import AcademicYear
        self.lab_year, _ = AcademicYear.objects.get_or_create(name='2026-2027', defaults={'is_current': True})

    def test_dean_can_create_degree_and_courses(self):
        self.client.login(username='dean_cat', password='ucjc1234')
        response = self.client.post(reverse('horarios:degree_create'), {
            'code': 'TST',
            'name': 'Grado de Prueba',
            'is_active': True,
            'provision_year': self.lab_year.pk,
        })
        degree = DegreeProgram.objects.get(code='TST')
        self.assertRedirects(response, reverse('horarios:degree_detail', kwargs={'pk': degree.pk}))
        self.assertEqual(Course.objects.filter(degree_program=degree, academic_year=self.lab_year).count(), 4)

    def test_dean_can_add_subject_to_degree(self):
        degree = DegreeProgram.objects.create(code='XINF', name='Informática Test', is_active=True)
        self.client.login(username='dean_cat', password='ucjc1234')
        response = self.client.post(
            reverse('horarios:subject_create') + f'?degree={degree.pk}',
            {
                'degree': degree.pk,
                'code': '99001',
                'name': 'Asignatura Test',
                'weekly_sessions': 2,
                'is_shared': False,
                'degree_programs': [degree.pk],
            },
        )
        self.assertEqual(Subject.objects.filter(code='99001').count(), 1)
        self.assertTrue(response.status_code, 302)

    def test_student_cannot_create_degree(self):
        student = create_user('stud_cat', 'STUD')
        self.client.login(username='stud_cat', password='ucjc1234')
        response = self.client.get(reverse('horarios:degree_create'))
        self.assertRedirects(response, reverse('horarios:dashboard'))
