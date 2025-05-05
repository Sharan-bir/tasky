from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import LeaveRequest
from .serializers import LeaveRequestSerializer, LeaveRequestUpdateSerializer
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        leave_request = serializer.save(user=self.request.user)
        self.send_leave_request_email(leave_request)

    def send_leave_request_email(self, leave_request):
        subject = 'New Leave Request'
        message = f'A new leave request has been submitted by {leave_request.user.email} from {leave_request.start_date} to {leave_request.end_date}.'
        recipient_list = [leave_request.user.company.default_email, 'another_email@example.com']
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_leaves(self, request):
        user_leaves = LeaveRequest.objects.filter(user=request.user)
        serializer = self.get_serializer(user_leaves, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        leave_request = self.get_object()
        if request.user.role in ['Project_manager', 'Team_lead']:
            leave_request.status = 'Approved'
            leave_request.reviewed_by = request.user
            leave_request.reviewed_at = timezone.now()
            leave_request.save()
            return Response({'status': 'Leave request approved'})
        return Response({'status': 'You do not have permission to approve this leave request'}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def reject(self, request, pk=None):
        leave_request = self.get_object()
        if request.user.role in ['Project_manager', 'Team_lead']:
            leave_request.status = 'Rejected'
            leave_request.reviewed_by = request.user
            leave_request.reviewed_at = timezone.now()
            leave_request.save()
            return Response({'status': 'Leave request rejected'})
        return Response({'status': 'You do not have permission to reject this leave request'}, status=status.HTTP_403_FORBIDDEN)
