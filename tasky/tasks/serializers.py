from rest_framework import serializers
from tasks.models import Project, ProjectTeam, Module, Task, TaskHistory, TaskComment
from account.models import User

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'company')

class ProjectTeamSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = ProjectTeam
        fields = '__all__'
        read_only_fields = ('joined_at',)

class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class TaskSerializer(serializers.ModelSerializer):
    assigned_to_email = serializers.EmailField(source='assigned_to.email', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    assigned_by_email = serializers.EmailField(source='assigned_by.email', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    module_name = serializers.CharField(source='module.name', read_only=True, allow_null=True)

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = (
            'created_at', 'updated_at', 'completed_at', 'project_owner_approved_at',
            'task_approval_time', 'verified_at', 'published_at'
        )

    def validate(self, data):
        # Ensure that if status is 'Issue', priority is also set to 'Issue'
        if data.get('status') == 'Issue':
            data['priority'] = 'Issue'
        return data

class TaskHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source='changed_by.email', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    
    class Meta:
        model = TaskHistory
        fields = '__all__'
        read_only_fields = ('changed_at',)

class TaskCommentSerializer(serializers.ModelSerializer):
    commented_by_email = serializers.EmailField(source='commented_by.email', read_only=True)
    commented_by_name = serializers.CharField(source='commented_by.get_full_name', read_only=True)
    
    class Meta:
        model = TaskComment
        fields = '__all__'
        read_only_fields = ('created_at',)