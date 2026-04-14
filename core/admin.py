from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Department, Grievance, StatusLog

admin.site.register(User, UserAdmin)
admin.site.register(Department)
admin.site.register(Grievance)
admin.site.register(StatusLog)
