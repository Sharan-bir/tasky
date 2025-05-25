from django.db import models
from django.utils import timezone
from account.models import User

class Project(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Archived', 'Archived'),
    ]
    
    company = models.ForeignKey('account.Company', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    resources = models.JSONField(blank=True, null=True)  # dictionary of URLs
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class ProjectTeam(models.Model):
    ROLE_CHOICES = [
        ('Project Manager', 'Project Manager'),
        ('Team Lead', 'Team Lead'),
        ('Sub Team Lead', 'Sub Team Lead'),
        ('Employee', 'Employee'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.role} in {self.project.name}"

    class Meta:
        unique_together = ('project', 'user')
        ordering = ['project', '-role']


class Module(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    class Meta:
        ordering = ['project', 'name']


class Task(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Under Approval', 'Under Approval'),
        ('Approved', 'Approved'),
        ('Issue', 'Issue'),
    ]
    
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
        ('Issue', 'Issue'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_tasks')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    description = models.TextField(null=True,blank=True)
    helper_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='helped_tasks')
    title = models.CharField(max_length=150)
    module = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    verified_by_project_owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owner_verified_tasks')
    project_owner_approved_at = models.DateTimeField(null=True, blank=True)
    task_approval_time = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_tasks')
    verified_at = models.DateTimeField(null=True, blank=True)
    published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    resources = models.JSONField(blank=True, null=True)  # array of URLs or resources
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # If status is changed to 'Issue', also set priority to 'Issue'
        if self.status == 'Issue':
            self.priority = 'Issue'
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']


class TaskHistory(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    under_approval_time = models.DateTimeField(null=True, blank=True)
    was_assigned = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history_assignments')
    old_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20)
    old_priority = models.CharField(max_length=10, null=True, blank=True)
    new_priority = models.CharField(max_length=10)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task.title} - {self.new_status} by {self.changed_by.email}"

    class Meta:
        ordering = ['-changed_at']


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    commented_by = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.commented_by.email} on {self.task.title}"

    class Meta:
        ordering = ['created_at']