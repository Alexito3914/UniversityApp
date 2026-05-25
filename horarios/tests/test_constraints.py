from datetime import time

from django.core.exceptions import ValidationError
from django.test import TestCase

from horarios.models import Course, DegreeProgram, SubjectOffering, TimeSlotConfig
from horarios.services import create_schedule_entry, generate_schedule_entries, validate_schedule_entry

from .base import add_schedule_entry, build_schedule_lab


class ScheduleConstraintsTests(TestCase):
    def setUp(self):
        lab = build_schedule_lab()
        self.__dict__.update(lab)

    def test_professor_conflict_same_slot(self):
        add_schedule_entry(self.schedule, self.offering_a, self.morning_slot)
        offering_same_prof = SubjectOffering.objects.create(
            subject=self.subj_b, course=self.course_morning, professor=self.prof_1, classroom=self.room_2, group_name='B',
        )
        with self.assertRaises(ValidationError):
            add_schedule_entry(self.schedule, offering_same_prof, self.morning_slot)

    def test_classroom_conflict_same_slot(self):
        add_schedule_entry(self.schedule, self.offering_a, self.morning_slot)
        offering_same_room = SubjectOffering.objects.create(
            subject=self.subj_b, course=self.course_morning, professor=self.prof_2, classroom=self.room_1, group_name='B',
        )
        with self.assertRaises(ValidationError):
            add_schedule_entry(self.schedule, offering_same_room, self.morning_slot)

    def test_course_conflict_same_slot(self):
        add_schedule_entry(self.schedule, self.offering_a, self.morning_slot)
        with self.assertRaises(ValidationError):
            add_schedule_entry(self.schedule, self.offering_b, self.morning_slot)

    def test_shift_rules_and_allowed_ranges(self):
        errors_morning_course_in_afternoon = validate_schedule_entry(self.schedule, self.offering_a, self.afternoon_slot)
        self.assertTrue(any('tarde' in e.lower() for e in errors_morning_course_in_afternoon))

        offering_4th = SubjectOffering.objects.create(
            subject=self.subj_b, course=self.course_afternoon, professor=self.prof_2, classroom=self.room_2, group_name='4A',
        )
        errors_4th_in_morning = validate_schedule_entry(self.schedule, offering_4th, self.morning_slot)
        self.assertTrue(any('tarde' in e.lower() for e in errors_4th_in_morning))

        errors_invalid_time = validate_schedule_entry(self.schedule, self.offering_a, self.invalid_slot)
        self.assertTrue(any('09:00-15:00' in e for e in errors_invalid_time))

    def test_generator_applies_max_hours_and_free_day(self):
        TimeSlotConfig.objects.filter(academic_year=self.year).exclude(pk=self.morning_slot.pk).delete()
        for day in ['MON', 'TUE', 'WED', 'THU', 'FRI']:
            for start_h, end_h in [(9, 11), (11, 13), (13, 15)]:
                TimeSlotConfig.objects.get_or_create(
                    academic_year=self.year,
                    day_of_week=day,
                    start_time=time(start_h, 0),
                    end_time=time(end_h, 0),
                    defaults={'is_active': True},
                )

        heavy_offering = SubjectOffering.objects.create(
            subject=self.subj_c, course=self.course_morning, professor=self.prof_1, classroom=self.room_1, group_name='HEAVY',
        )
        result = generate_schedule_entries(self.schedule, clear_existing=True, free_day='MON')

        created_for_heavy = self.schedule.entries.filter(subject_offering=heavy_offering).count()
        self.assertLessEqual(created_for_heavy, 10)
        self.assertGreaterEqual(result['created'], created_for_heavy)
        self.assertFalse(
            self.schedule.entries.filter(subject_offering=heavy_offering, timeslot__day_of_week='MON').exists()
        )

    def test_generator_filters_by_course_id(self):
        result = generate_schedule_entries(self.schedule, clear_existing=True, course_id=self.course_morning.pk)
        self.assertGreater(result['created'], 0)
        for entry in self.schedule.entries.all():
            self.assertEqual(entry.subject_offering.course_id, self.course_morning.pk)

    def test_generator_filters_by_course_number_all_degrees(self):
        other_degree = DegreeProgram.objects.create(code='ROB-T', name='Robotica Test', is_active=True)
        other_course = Course.objects.create(
            degree_program=other_degree, academic_year=self.year, number=1, shift='MORNING',
        )
        SubjectOffering.objects.create(
            subject=self.subj_b, course=other_course, professor=self.prof_2, classroom=self.room_2, group_name='R1',
        )
        result = generate_schedule_entries(self.schedule, clear_existing=True, course_number=1)
        self.assertGreater(result['created'], 0)
        course_ids = set(self.schedule.entries.values_list('subject_offering__course_id', flat=True))
        self.assertIn(self.course_morning.pk, course_ids)
        self.assertIn(other_course.pk, course_ids)
        for entry in self.schedule.entries.all():
            self.assertEqual(entry.subject_offering.course.number, 1)

    def test_fourth_year_specialty_groups_can_share_slot(self):
        off_ti = SubjectOffering.objects.create(
            subject=self.subj_a, course=self.course_afternoon, professor=self.prof_1,
            classroom=self.room_1, group_name='4INF-TI',
        )
        off_is = SubjectOffering.objects.create(
            subject=self.subj_b, course=self.course_afternoon, professor=self.prof_2,
            classroom=self.room_2, group_name='4INF-IS',
        )
        add_schedule_entry(self.schedule, off_ti, self.afternoon_slot)
        add_schedule_entry(self.schedule, off_is, self.afternoon_slot)
        self.assertEqual(self.schedule.entries.filter(timeslot=self.afternoon_slot).count(), 2)

        off_ti_b = SubjectOffering.objects.create(
            subject=self.subj_c, course=self.course_afternoon, professor=self.prof_1,
            classroom=self.room_2, group_name='4INF-TI',
        )
        with self.assertRaises(ValidationError):
            add_schedule_entry(self.schedule, off_ti_b, self.afternoon_slot)
