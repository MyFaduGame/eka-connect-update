from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserDeviceAssignment

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    pass

admin.site.register(UserDeviceAssignment)