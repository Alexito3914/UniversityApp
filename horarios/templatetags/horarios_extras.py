"""Filtros de template personalizados para el sistema de horarios."""
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Permite acceder a valores de un diccionario con una variable como clave."""
    return dictionary.get(key)


@register.filter
def prof_short_name(professor):
    """Nombre y primer apellido del profesor (prioriza el texto del Excel)."""
    if not professor:
        return ''
    raw = (getattr(professor, 'display_name', None) or '').strip()
    if raw:
        if ',' in raw:
            last_part, first_part = raw.split(',', 1)
            first_surname = (last_part.strip().split()[0] if last_part.strip() else '')
            first_name = (first_part.strip().split()[0] if first_part.strip() else '')
            return f'{first_name} {first_surname}'.strip()
        bits = raw.split()
        if len(bits) >= 2:
            return f'{bits[0]} {bits[1]}'
        return raw
    first_surname = (professor.last_name or '').split()[0]
    return f'{professor.first_name} {first_surname}'.strip()


@register.filter
def offering_degree_course(offering):
    """Titulación y curso de una oferta docente."""
    if not offering or not offering.course_id:
        return ''
    course = offering.course
    code = course.degree_program.code if course.degree_program_id else '—'
    return f'{code} · {course.number}º'
