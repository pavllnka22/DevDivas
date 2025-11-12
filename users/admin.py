from django.contrib import admin

from users.models import CustomUser


# Register your models here.

@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active', 'is_email_verified', 'is_staff')
    search_fields = ('username', 'email')