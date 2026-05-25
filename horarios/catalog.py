"""Utilidades para el catálogo académico (titulaciones, cursos)."""

from .models import AcademicYear, Course, DegreeProgram


def course_shift_for(degree_code, course_number):
    if degree_code == 'DINFROB':
        return 'AFTERNOON' if course_number >= 4 else 'MORNING'
    return 'AFTERNOON' if course_number == 4 else 'MORNING'


def max_courses_for_degree(degree_code):
    return 5 if degree_code == 'DINFROB' else 4


def provision_courses_for_degree(degree, academic_year=None):
    """Crea cursos 1º–4º (o 1º–5º doble grado) para la titulación en el año indicado."""
    if academic_year is None:
        academic_year = AcademicYear.objects.filter(is_current=True).first()
    if not academic_year:
        return []
    created = []
    for number in range(1, max_courses_for_degree(degree.code) + 1):
        course, was_created = Course.objects.get_or_create(
            degree_program=degree,
            academic_year=academic_year,
            number=number,
            defaults={'shift': course_shift_for(degree.code, number)},
        )
        if was_created:
            created.append(course)
    return created
