from rest_framework import serializers
from .models import LeaveRequest

class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ['user', 'status', 'reviewed_by', 'reviewed_at', 'created_at', 'updated_at']

class LeaveRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ['status', 'reviewed_by', 'reviewed_at']
