from rest_framework import viewsets, status,permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from datetime import date
from attendance.models import LoginLogout
from account.models import UserInfo,User
from attendance.serializers import LoginLogoutSerializer

import csv
from django.db import models
from datetime import timedelta
from django.http import HttpResponse
from django.db.models.functions import TruncDate
from django.db.models import Sum,Q

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = LoginLogout.objects.all()
    serializer_class = LoginLogoutSerializer
    permission_classes = [permissions.IsAuthenticated]

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

    @action(detail=False, methods=['get'],url_path=r'(?P<pk>\d+)/daily_summary')
    def daily_summary(self, request,pk=None):
        """Get current user's daily summary or date range summary"""
        date_param = request.query_params.get('date')
        start_date_param = request.query_params.get('start_date')
        end_date_param = request.query_params.get('end_date')
        
        try:
            user = UserInfo.objects.get(id=pk)
            print(user)
        except User.DoesNotExist:
            return Response(
            {"error": "User not found"},
            status=status.HTTP_404_NOT_FOUND
            )
    
        # Filter queryset by the specified user
        queryset = LoginLogout.objects.filter(user=user)
        
        # Handle single date case
        if date_param:
            try:
                target_date = date.fromisoformat(date_param)
                queryset = queryset.filter(date=target_date)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        # Handle date range case
        elif start_date_param or end_date_param:
            try:
                start_date = date.fromisoformat(start_date_param) if start_date_param else date.min
                end_date = date.fromisoformat(end_date_param) if end_date_param else date.max
                
                if start_date > end_date:
                    return Response(
                        {"error": "Start date must be before or equal to end date"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                queryset = queryset.filter(date__range=(start_date, end_date))
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        # Default to today if no params
        else:
            queryset = queryset.filter(date=date.today())
        
        # Group by date for range queries, single date will have one group
        if date_param or (not start_date_param and not end_date_param):
            total_duration = queryset.aggregate(total=Sum('duration'))['total']
            return Response({
                'date': date_param or str(date.today()),
                'total_duration': str(total_duration) if total_duration else "00:00:00",
                # 'sessions': self.get_serializer(queryset, many=True).data
            })
        else:
            # For date ranges, return daily breakdown
            daily_data = queryset.annotate(
                day=TruncDate('login_time')
            ).values('day').annotate(
                total_duration=Sum('duration'),
                session_count=models.Count('id')  # This is where the error was
            ).order_by('day')
            
            # Convert timedelta to string for JSON serialization
            for day in daily_data:
                day['total_duration'] = str(day['total_duration']) if day['total_duration'] else "00:00:00"
            
            return Response({
                'start_date': start_date_param,
                'end_date': end_date_param,
                'daily_summaries': daily_data,
                # 'sessions': self.get_serializer(queryset, many=True).data
            })

    # Add this new action to AttendanceViewSet
    @action(detail=False, methods=['get'])
    def monthly_report_csv(self, request):
        """Generate a CSV report of monthly login durations for all users in the same company, grouped by day."""
        # Get month and year from query params (default to current month)
        year = request.query_params.get("year", timezone.now().year)
        month = request.query_params.get("month", timezone.now().month)
        try:
            year = int(year)
            month = int(month)
            start_date = date(year, month, 1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        except (ValueError, TypeError):
            return Response({"error": "Invalid year or month parameters"}, status=status.HTTP_400_BAD_REQUEST)

        # Get the company
        try:
            company = request.user.company
            if not company:
                return Response({"error": "Company not found for the current user."}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({"error": "Error retrieving company information"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Get all active users in the company
        try:
            # Get all users in company for summary
            all_company_users = User.objects.filter(company=company)
            
            # Get active users for processing
            company_users = User.objects.filter(company=company, is_active=True).select_related('info')
            
            if company_users.count() == 0:
                return Response({"error": "No active users found in company"}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({"error": "Error retrieving company users"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Process attendance data for each user
        flat_rows = []
        total_records = 0
        
        for user in company_users:
            try:
                user_info = user.info
                
                # Get attendance records for this user
                user_records = LoginLogout.objects.filter(
                    user=user_info,
                    date__range=(start_date, end_date)
                ).order_by('date')
                
                record_count = user_records.count()
                total_records += record_count
                
                if record_count > 0:
                    # Group by date and calculate totals
                    daily_data = user_records.annotate(
                        day=TruncDate('login_time')
                    ).values('day').annotate(
                        total_duration=Sum('duration'),
                        session_count=models.Count('id')
                    ).order_by('day')
                    
                    for day_data in daily_data:
                        day = day_data['day']
                        duration = day_data['total_duration']
                        sessions = day_data['session_count']
                        
                        # Convert duration to string format
                        duration_str = str(duration).split('.')[0] if duration else "00:00:00"
                        
                        flat_rows.append((day,user.info.first_name, user.email, duration_str, sessions))
                
            except UserInfo.DoesNotExist:
                continue
            except Exception:
                continue

        if not flat_rows:
            return Response({"error": "No attendance data found for the specified period"}, status=status.HTTP_404_NOT_FOUND)

        # Sort rows by date and user email
        flat_rows.sort(key=lambda x: (x[0], x[1]))
        
        # Create CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename=company_attendance_report_{year}_{month}.csv"
        writer = csv.writer(response)
        
        # Write headers
        writer.writerow(["Company Monthly Attendance Report - Daily Breakdown"])
        writer.writerow([f"Company: {company.name}"])
        writer.writerow([f"Report Period: {start_date} to {end_date}"])
        writer.writerow([f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        writer.writerow([])  # Empty row
        writer.writerow(["Date","User Name", "User Email", "Total Duration", "Session Count"])
        
        # Write data rows
        for day,user_name, email, duration, sessions in flat_rows:
            writer.writerow([day.strftime("%Y-%m-%d"), user_name,email, duration, sessions])
        
        # Add summary
        writer.writerow([])
        writer.writerow(["Report Summary"])
        writer.writerow([f"Total Users in Company: {all_company_users.count()}"])
        writer.writerow([f"Active Users: {company_users.count()}"])
        writer.writerow([f"Users with Attendance Data: {len(set(row[1] for row in flat_rows))}"])
        writer.writerow([f"Total Records: {total_records}"])
        writer.writerow([f"Report Period: {start_date} to {end_date}"])
        
        return response

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
            'session_count': queryset.count(),
            'sessions': self.get_serializer(queryset, many=True).data
        })