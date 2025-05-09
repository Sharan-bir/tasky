from rest_framework import serializers
from .models import LeaveRequest
from django.core.exceptions import ValidationError

class LeaveRequestSerializer(serializers.ModelSerializer):
    attachment = serializers.FileField(required=False)
    reason = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    
    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ['user', 'status', 'reviewed_by', 'reviewed_at', 'created_at', 'updated_at', 'reason']
    
    def validate(self, data):
        # Validate that start_date is not after end_date
        if 'start_date' in data and 'end_date' in data:
            if data['start_date'] > data['end_date']:
                raise ValidationError({"end_date": "End date should be after start date."})
        return data

class LeaveRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ['status', 'reviewed_by', 'reviewed_at']

class LeaveStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['Approved', 'Rejected'])
    comment = serializers.CharField(required=False, allow_blank=True)