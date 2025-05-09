from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import LeaveRequest
from .serializers import LeaveRequestSerializer, LeaveRequestUpdateSerializer, LeaveStatusUpdateSerializer
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q

class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        email_subject = self.request.data.get('reason', 'New Leave Request')
        email_message = self.request.data.get('description', '')
        
        leave_request = serializer.save(user=self.request.user)
        
        # Send email with attachment if provided
        self.send_leave_request_email(leave_request, email_subject, email_message)
        
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def send_leave_request_email(self, leave_request, subject, message):
        # Prepare email
        default_subject = f'Leave Request: {leave_request.start_date} to {leave_request.end_date}'
        email_subject = subject if subject else default_subject
        
        default_message = f'A new leave request has been submitted by {leave_request.user.email} from {leave_request.start_date} to {leave_request.end_date}.\n\nReason: {leave_request.reason}\n\nDescription: {leave_request.description or "N/A"}'
        email_message = message if message else default_message
        
        # Create email object
        email = EmailMessage(
            subject=email_subject,
            body=email_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[leave_request.user.email]
        )
        
        # Attach file if it exists
        if leave_request.attachment:
            email.attach_file(leave_request.attachment.path)
        
        # Send email
        email.send()

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_leaves(self, request):
        user_leaves = LeaveRequest.objects.filter(user=request.user)
        serializer = self.get_serializer(user_leaves, many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def company_leaves(self, request):
        """Get all leave requests from the company"""
        company = request.user.company
        company_leaves = LeaveRequest.objects.filter(user__company=company)
       
        if not request.user.role in ['Project_manager', 'Team_lead', 'Company_owner']:
            company_leaves = company_leaves.filter(user=request.user)
        
        serializer = self.get_serializer(company_leaves, many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def get_leave(self, request, pk=None):
        """Get a specific leave request"""
        company = request.user.company
        try:
            leave_request = LeaveRequest.objects.get(id=pk,user__company=company)
        except:
            return Response(
                {'detail': 'You do not have permission to view this leave request'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if user has permission to view this leave
        if request.user != leave_request.user and not request.user.role in ['Project_manager', 'Team_lead', 'Company_owner']:
            return Response(
                {'detail': 'You do not have permission to view this leave request'}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data,status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def update_status(self, request, pk=None):
        """Unified endpoint for approving or rejecting leave requests"""
        leave_request = self.get_object()
        serializer = LeaveStatusUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        # Check permissions
        if request.user.role not in ['Project_manager', 'Team_lead','Company_owner']:
            return Response(
                {'detail': 'You do not have permission to update this leave request'}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Update the leave request
        leave_request.status = serializer.validated_data['status']
        leave_request.reviewed_by = request.user
        leave_request.reviewed_at = timezone.now()
        leave_request.save()
        
        # Send notification email to the user
        status_text = "approved" if leave_request.status == "Approved" else "Rejected"
        subject = f"Leave Request {status_text.capitalize()}"
        message = f"Your leave request from {leave_request.start_date} to {leave_request.end_date} has been {status_text}."
        
        if 'comment' in serializer.validated_data and serializer.validated_data['comment']:
            message += f"\n\nComments: {serializer.validated_data['comment']}"
        
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[leave_request.user.email]
        )
        email.send()
        
        return Response({'status': f'Leave request {status_text}'}, status=status.HTTP_200_OK)
        
    # Keep these methods for backward compatibility but make them use update_status
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        request.data['status'] = 'Approved'
        return self.update_status(request, pk)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def reject(self, request, pk=None):
        request.data['status'] = 'Rejected'
        return self.update_status(request, pk)