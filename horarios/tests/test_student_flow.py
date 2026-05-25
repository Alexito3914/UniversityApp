from django.test import TestCase
from django.urls import reverse

from horarios.models import Course, Schedule, ScheduleEntry

from .base import add_schedule_entry, build_schedule_lab, create_user


class StudentScheduleFlowTests(TestCase):
    def setUp(self):
        lab = build_schedule_lab()
        self.year = lab['year']
        self.degree = lab['degree']
        self.course = Course.objects.create(
            degree_program=self.degree, academic_year=self.year, number=2, shift='MORNING',
        )
        self.schedule = Schedule.objects.create(name='Horario Test', academic_year=self.year, status='APPROVED')
        create_user('estudiante_test', 'STUD')

    def test_student_redirected_to_setup_without_course(self):
        self.client.login(username='estudiante_test', password='ucjc1234')
        response = self.client.get(reverse('horarios:home'))
        self.assertRedirects(response, reverse('horarios:student_schedule_setup'))

    def test_student_setup_stores_course_and_opens_schedule(self):
        self.client.login(username='estudiante_test', password='ucjc1234')
        response = self.client.post(reverse('horarios:student_schedule_setup'), {
            'academic_year': self.year.pk,
            'degree': self.degree.pk,
            'course_number': '2',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'/horarios/{self.schedule.pk}/', response.request['PATH_INFO'])

    def test_student_schedule_detail_forces_course_filter(self):
        self.client.login(username='estudiante_test', password='ucjc1234')
        self.client.post(reverse('horarios:student_schedule_setup'), {
            'academic_year': self.year.pk,
            'degree': self.degree.pk,
            'course_number': '2',
        })
        response = self.client.get(reverse('horarios:schedule_detail', kwargs={'pk': self.schedule.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_student_view'])
        self.assertEqual(str(response.context['selected_course']), str(self.course.pk))

    def test_student_cannot_access_other_year_schedule(self):
        from horarios.models import AcademicYear
        other = AcademicYear.objects.create(name='2098-2099', is_current=False)
        other_schedule = Schedule.objects.create(name='Otro año', academic_year=other, status='APPROVED')
        self.client.login(username='estudiante_test', password='ucjc1234')
        self.client.post(reverse('horarios:student_schedule_setup'), {
            'academic_year': self.year.pk,
            'degree': self.degree.pk,
            'course_number': '2',
        })
        response = self.client.get(reverse('horarios:schedule_detail', kwargs={'pk': other_schedule.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('horarios:student_my_schedule'))
