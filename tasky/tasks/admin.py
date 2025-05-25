from django.contrib import admin
from .models import Project, ProjectTeam, Module, Task, TaskHistory, TaskComment

class ProjectTeamInline(admin.TabularInline):
    model = ProjectTeam
    extra = 1
    fields = ('user', 'role', 'joined_at')
    readonly_fields = ('joined_at',)

class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    fields = ('title', 'assigned_to', 'status', 'priority', 'deadline')
    readonly_fields = ('created_at', 'updated_at')

class TaskHistoryInline(admin.TabularInline):
    model = TaskHistory
    extra = 1
    fk_name = 'task'  # Specify which foreign key to use
    fields = ('changed_by', 'new_status', 'new_priority', 'changed_at')
    readonly_fields = ('changed_at',)

class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 1
    fields = ('commented_by', 'comment', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'status', 'created_at')
    list_filter = ('status', 'company')
    search_fields = ('name', 'description')
    inlines = [ProjectTeamInline, TaskInline]
    fieldsets = (
        (None, {
            'fields': ('company', 'name', 'status')
        }),
        ('Details', {
            'fields': ('description', 'resources'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'readonly_fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(ProjectTeam)
class ProjectTeamAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'role', 'joined_at')
    list_filter = ('role', 'project')
    search_fields = ('user__email', 'project__name')
    readonly_fields = ('joined_at',)

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'created_at')
    list_filter = ('project',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assigned_to', 'status', 'priority', 'deadline')
    list_filter = ('status', 'priority', 'project')
    search_fields = ('title',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TaskHistoryInline, TaskCommentInline]
    fieldsets = (
        (None, {
            'fields': ('project', 'module', 'title','description')
        }),
        ('Assignment', {
            'fields': ('assigned_by', 'assigned_to', 'helper_user')
        }),
        ('Status', {
            'fields': ('status', 'priority', 'completed', 'deadline')
        }),
        ('Verification', {
            'fields': ('verified_by', 'verified_at', 'verified_by_project_owner', 'project_owner_approved_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ('task', 'changed_by', 'new_status', 'new_priority', 'changed_at')
    list_filter = ('new_status', 'new_priority')
    search_fields = ('task__title', 'changed_by__email')
    readonly_fields = ('changed_at',)

@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'commented_by', 'created_at')
    list_filter = ('task__project',)
    search_fields = ('comment', 'task__title', 'commented_by__email')
    readonly_fields = ('created_at',)