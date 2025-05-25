from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from tasks.models import Project, ProjectTeam, Module, Task, TaskHistory, TaskComment
from tasks.serializers import (
    ProjectSerializer, ProjectTeamSerializer, ModuleSerializer,
    TaskSerializer, TaskHistorySerializer, TaskCommentSerializer
)
from account.models import User

class IsProjectManagerOrTeamLead(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['Project_manager', 'Team_lead']

class IsProjectManagerOrTeamLeadOrSubTeamLead(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['Project_manager', 'Team_lead', 'Sub_team_lead']

class IsAssignedToTask(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.assigned_to == request.user

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectManagerOrTeamLead]

    def get_queryset(self):
        # Users can only see projects from their company
        return Project.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

class ProjectTeamViewSet(viewsets.ModelViewSet):
    queryset = ProjectTeam.objects.all()
    serializer_class = ProjectTeamSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectManagerOrTeamLead]

    def get_queryset(self):
        # Filter by project if project_id is provided
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return ProjectTeam.objects.filter(project_id=project_id)
        return ProjectTeam.objects.filter(project__company=self.request.user.company)

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter by project if project_id is provided
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return Module.objects.filter(project_id=project_id)
        return Module.objects.filter(project__company=self.request.user.company)

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Task.objects.filter(project__company=user.company)
        
        # Employees can only see tasks assigned to them or in their domain
        if user.role == 'Employee':
            queryset = queryset.filter(assigned_to=user)
        
        # Filter by project if project_id is provided
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            
        # Filter by module if module_id is provided
        module_id = self.request.query_params.get('module_id')
        if module_id:
            queryset = queryset.filter(module_id=module_id)
            
        # Filter by status if status is provided
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # Filter by priority if priority is provided
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
            
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in ['Project_manager', 'Team_lead', 'Sub_team_lead']:
            raise Response({'detail': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN)
        
        task = serializer.save(assigned_by=user)
        
        # Create initial task history
        TaskHistory.objects.create(
            task=task,
            changed_by=user,
            was_assigned=task,
            old_status=None,
            new_status=task.status,
            old_priority=None,
            new_priority=task.priority
        )

    def perform_update(self, serializer):
        task = self.get_object()
        old_status = task.status
        old_priority = task.priority
        user = self.request.user
        
        updated_task = serializer.save()
        
        # Check if status or priority changed
        if old_status != updated_task.status or old_priority != updated_task.priority:
            TaskHistory.objects.create(
                task=updated_task,
                changed_by=user,
                was_assigned=updated_task,
                old_status=old_status,
                new_status=updated_task.status,
                old_priority=old_priority,
                new_priority=updated_task.priority,
                under_approval_time=timezone.now() if updated_task.status == 'Under Approval' else None
            )
            
            # If task is under approval and then marked as issue
            if old_status == 'Under Approval' and updated_task.status == 'Issue':
                updated_task.priority = 'Issue'
                updated_task.save()

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        user = request.user
        
        if user != task.assigned_to:
            return Response(
                {'detail': 'Only the assigned user can mark the task as completed.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        task.status = 'Under Approval'
        task.completed = True
        task.completed_at = timezone.now()
        task.save()
        
        return Response({'status': 'Task marked as completed and sent for approval'})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        task = self.get_object()
        user = request.user
        
        if user.role not in ['Project_manager', 'Team_lead']:
            return Response(
                {'detail': 'Only Project Managers and Team Leads can approve tasks.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        if task.status != 'Under Approval':
            return Response(
                {'detail': 'Task is not in Under Approval status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        task.status = 'Approved'
        task.verified_by = user
        task.verified_at = timezone.now()
        
        if user.role == 'Project_manager':
            task.verified_by_project_owner = user
            task.project_owner_approved_at = timezone.now()
            
        task.save()
        
        return Response({'status': 'Task approved'})

    @action(detail=True, methods=['post'])
    def mark_as_issue(self, request, pk=None):
        task = self.get_object()
        user = request.user
        
        if user.role not in ['Project_manager', 'Team_lead', 'Sub_team_lead'] and user != task.assigned_to:
            return Response(
                {'detail': 'You do not have permission to mark this task as an issue.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        task.status = 'Issue'
        task.priority = 'Issue'
        task.save()
        
        return Response({'status': 'Task marked as issue'})

class TaskHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TaskHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.request.query_params.get('task_id')
        if task_id:
            return TaskHistory.objects.filter(task_id=task_id)
        return TaskHistory.objects.filter(task__project__company=self.request.user.company)

class TaskCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.request.query_params.get('task_id')
        if task_id:
            return TaskComment.objects.filter(task_id=task_id)
        return TaskComment.objects.filter(task__project__company=self.request.user.company)

    def perform_create(self, serializer):
        task_id = self.request.data.get('task')
        task = get_object_or_404(Task, id=task_id)
        
        # Check if user is part of the project team or assigned to the task
        if not ProjectTeam.objects.filter(project=task.project, user=self.request.user).exists() and \
           task.assigned_to != self.request.user:
            raise permissions.PermissionDenied("You don't have permission to comment on this task.")
        
        serializer.save(commented_by=self.request.user)