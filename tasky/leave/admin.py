from django.contrib import admin
from .models import LeaveRequest

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'start_date', 'end_date', 'status', 'reviewed_by')
    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('user__email', 'reason')
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'start_date', 'end_date')
        }),
        ('Leave Details', {
            'fields': ('reason', 'description','attachment')
        }),
        ('Approval Information', {
            'fields': ('status', 'reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )