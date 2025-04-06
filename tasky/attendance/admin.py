from django.contrib import admin
from .models import LoginLogout
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(LoginLogout)
class LoginLogoutAdmin(admin.ModelAdmin):
    list_display = ('get_user_email', 'date', 'login_time', 'logout_time', 'formatted_duration')
    list_filter = ('date',)
    search_fields = ('user__user__email', 'user__user__first_name', 'user__user__last_name')  # Updated path
    readonly_fields = ('date', 'duration')
    ordering = ('-date', '-login_time')

    def get_user_email(self, obj):
        return obj.user.user.email  # Access through user.user relationship
    get_user_email.short_description = 'User Email'
    get_user_email.admin_order_field = 'user__user__email'  # Updated path

    def formatted_duration(self, obj):
        if obj.duration:
            total_seconds = obj.duration.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        return "N/A"
    formatted_duration.short_description = 'Duration'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user__user')  # Optimize queries