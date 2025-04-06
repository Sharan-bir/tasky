from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Sum
from datetime import date
from attendance.models import LoginLogout
from account.models import UserInfo
from attendance.serializers import LoginLogoutSerializer

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = LoginLogout.objects.all()
    serializer_class = LoginLogoutSerializer

    def get_queryset(self):
        """Users can only see their own attendance records"""
        queryset = super().get_queryset().filter(user__user=self.request.user)
        
        # Optional date filtering
        date_param = self.request.query_params.get('date')
        if date_param:
            queryset = queryset.filter(date=date_param)
        
        return queryset

    @action(detail=False, methods=['post'])
    def login(self, request):
        """User can only log themselves in"""
        try:
            user_info = request.user.info
        except UserInfo.DoesNotExist:
            return Response(
                {"error": "User profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check for existing open session
        if LoginLogout.objects.filter(
            user=user_info,
            logout_time__isnull=True
        ).exists():
            return Response(
                {"error": "You already have an active session"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create new login record
        login_record = LoginLogout.objects.create(
            user=user_info,
            login_time=timezone.now(),
            date=timezone.now().date()
        )

        # Update user status
        user_info.status = UserInfo.StatusChoices.ONLINE
        user_info.save()

        return Response(
            self.get_serializer(login_record).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """User can only log themselves out"""
        try:
            user_info = request.user.info
        except UserInfo.DoesNotExist:
            return Response(
                {"error": "User profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get active session
        login_record = LoginLogout.objects.filter(
            user=user_info,
            logout_time__isnull=True
        ).order_by('-login_time').first()

        if not login_record:
            return Response(
                {"error": "No active session found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update logout time
        login_record.logout_time = timezone.now()
        login_record.save()

        # Update user status
        user_info.status = UserInfo.StatusChoices.OFFLINE
        user_info.save()

        return Response(self.get_serializer(login_record).data)

    @action(detail=False, methods=['get'])
    def daily_summary(self, request):
        """Get current user's daily summary"""
        date_param = request.query_params.get('date', str(date.today()))
        
        try:
            target_date = date.fromisoformat(date_param)
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(date=target_date)
        total_duration = queryset.aggregate(total=Sum('duration'))['total']

        return Response({
            'date': date_param,
            'total_duration': str(total_duration) if total_duration else "00:00:00",
            'sessions': self.get_serializer(queryset, many=True).data
        })

    @action(detail=False, methods=['get'])
    def user_sessions(self, request):
        """Get current user's session history"""
        queryset = self.get_queryset()
        
        # Optional date filtering
        date_param = request.query_params.get('date')
        if date_param:
            try:
                target_date = date.fromisoformat(date_param)
                queryset = queryset.filter(date=target_date)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response({
            'count': queryset.count(),
            'sessions': self.get_serializer(queryset, many=True).data
        })