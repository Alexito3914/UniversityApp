from django.contrib import admin
from .models import (
    AcademicYear,
    Classroom,
    Course,
    DegreeProgram,
    Enrollment,
    Notification,
    Professor,
    ProfessorAvailability,
    Schedule,
    ScheduleEntry,
    Student,
    Subject,
    SubjectOffering,
    TimeSlotConfig,
    UserProfile,
)

admin.site.register(UserProfile)
admin.site.register(DegreeProgram)
admin.site.register(AcademicYear)
admin.site.register(Course)
admin.site.register(Professor)
admin.site.register(Student)
admin.site.register(Classroom)
admin.site.register(TimeSlotConfig)
admin.site.register(Subject)
admin.site.register(SubjectOffering)
admin.site.register(ProfessorAvailability)
admin.site.register(Schedule)
admin.site.register(ScheduleEntry)
admin.site.register(Enrollment)
admin.site.register(Notification)
