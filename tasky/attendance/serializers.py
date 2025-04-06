from rest_framework import serializers
from attendance.models import LoginLogout
from account.models import UserInfo
from django.utils import timezone

class LoginLogoutSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=UserInfo.objects.all(),
        source='user'
    )
    email = serializers.CharField(source='user.user.email', read_only=True)
    date = serializers.DateField(read_only=True)
    duration = serializers.DurationField(read_only=True)

    class Meta:
        model = LoginLogout
        fields = [
            'id', 'user_id', 'email', 'login_time', 
            'logout_time', 'date', 'duration'
        ]
        read_only_fields = ['id', 'date', 'duration']

    def validate(self, data: dict) -> dict:
        # Ensure logout_time is after login_time if both are provided
        if data.get('logout_time') and data['login_time'] > data['logout_time']:
            raise serializers.ValidationError("Logout time must be after login time")
        return data