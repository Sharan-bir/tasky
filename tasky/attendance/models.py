from django.db import models
from account.models import UserInfo
from django.utils import timezone

class LoginLogout(models.Model):
    user = models.ForeignKey(
        UserInfo, 
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    login_time = models.DateTimeField()
    logout_time = models.DateTimeField(null=True, blank=True)
    date = models.DateField()
    duration = models.DurationField(null=True, blank=True)

    class Meta:
        db_table = 'login_logout'
        ordering = ['-date', '-login_time']

    def save(self, *args, **kwargs):
        # Auto-set the date field based on login_time
        if self.login_time and not self.date:
            self.date = self.login_time.date()
        
        # Calculate duration if both login and logout times are present
        if self.logout_time and self.login_time:
            self.duration = self.logout_time - self.login_time
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.user.email} - {self.date} - {self.duration}"