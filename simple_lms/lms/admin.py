from django.contrib import admin
from .models import *

admin.site.register(Course)
admin.site.register(CourseMember)
admin.site.register(CourseContent)
admin.site.register(Comment)
admin.site.register(Enrollment)
admin.site.register(ContentProgress)
admin.site.register(Note)
admin.site.register(Certificate)
admin.site.register(CommentReply)