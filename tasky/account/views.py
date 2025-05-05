from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import action
from django.contrib.auth import logout
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
import random
import string,datetime
from django.db.models import Q
from django.core.cache import cache
from account.models import User, Company,Domain, UserInfo
from account.serializers import (
    CompanySerializer, DomainSerializer,UserInfoSerializer,
    UserSerializer, RegisterCompanySerializer, LoginSerializer,
    RefreshTokenSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,RegisterEmployeeSerializer
)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = LoginSerializer

class DomainViewSet(viewsets.ModelViewSet):
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Domain.objects.none()
        queryset = super().get_queryset().exclude(name='all')
        if self.action == 'list':
            queryset = queryset.filter(company=self.request.user.company, is_active=True)
        elif self.action == 'retrieve':
            queryset = queryset.filter(is_active=True)
        return queryset

    def create(self, request, *args, **kwargs):
        if request.user.role not in ['Project_manager', 'Team_lead', 'Company_owner']:
            return Response(
                {'detail': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        if request.user.role not in ['Project_manager', 'Team_lead', 'Company_owner']:
            return Response(
                {'detail': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role not in ['Project_manager', 'Team_lead', 'Company_owner']:
            return Response(
                {'detail': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        domain = self.get_object()
        domain.is_active = False
        domain.save()
        return Response(
            {'detail': 'Domain has been deactivated.'},
            status=status.HTTP_200_OK
        )

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            if self.request.user.role == 'Company_owner':
                return [permissions.IsAuthenticated()]
            else:
                return [permissions.BasePermission()]
        elif self.action == 'list':
            if self.request.user.is_superuser:
                return [permissions.IsAuthenticated()]
            else:
                return [permissions.BasePermission()]
        return super().get_permissions()
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return Company.objects.all()
        else:
            return Company.objects.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        serializer = RegisterCompanySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            company = serializer.save()
            user = User.objects.filter(company=company).first()

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            return Response({
                    'id': company.id,
                    'name': company.name,
                    'email': user.email,
                    'role': user.role,
                    'access_token': access_token
                }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = CompanySerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.is_active = False
            instance.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Customize the queryset to filter users by company
        if self.request.user.is_authenticated:
            return User.objects.filter(company=self.request.user.company,is_active=True)
        return User.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = UserSerializer(queryset, many=True)
        custom_data = []
        for user in serializer.data:
            custom_data.append({
                'id': user['id'],
                'email': user['email'],
                'role': user['role'],
                'address': user['info']['address'] if user.get('info') else None,
                'status': user['info']['status'] if user.get('info') else None,
            })

        return Response(custom_data)
        # return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        if request.user.role not in ['Company_owner', 'Project_manager']:
            return Response(
                {'detail': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )

        email = request.data.get('email')

        try:
            user = User.objects.get(email=email)
            return Response(
                {'id': user.id, 'email': user.email, 'role': user.role},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            
            serializer = RegisterEmployeeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            return Response(
                {'id': user.id, 'email': user.email, 'role': user.role},
                status=status.HTTP_201_CREATED
            )
        
    def update(self, request, *args, **kwargs):
        user = self.get_object()

        if request.user.role in ['Company_owner', 'Project_manager']:
            serializer = UserSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(
                {'detail': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )

    def destroy(self, request, *args, **kwargs):
        if request.user.role not in ['Company_owner', 'Project_manager']:
            return Response(
                {'detail': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response(
            {'detail': 'User has been deactivated.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['put'],permission_classes=[permissions.IsAuthenticated])
    def update_user_info(self, request, pk=None):
        user = self.get_object()
        user_info = user.info
        if request.user != user:
            return Response(
                {'detail': 'You do not have permission to update this user\'s info.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = UserInfoSerializer(user_info, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['get'],permission_classes=[permissions.IsAuthenticated])
    def search_user(self, request):
        role = request.query_params.get('role', '')
        domain = request.query_params.get('domain', '')
        email = request.query_params.get('email', '')
         
        if role:
            users = User.objects.filter(role=role,company=request.user.company, is_active=True)
            
        elif domain:
            users = User.objects.filter(domain=domain,company=request.user.company, is_active=True)
           
        elif email:
            users = User.objects.filter(email=email,company=request.user.company, is_active=True)

        else:
            return Response(
                {'detail': 'Parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'],permission_classes=[permissions.IsAuthenticated])
    def view_user_info(self, request):
        user_info = request.user.info
        serializer = UserInfoSerializer(user_info)
        return Response(serializer.data)
    
class AuthViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def logout(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            logout(request)
        except Exception as e:
            pass
        return Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def refresh(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], authentication_classes=[])
    def forgot_password(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        cache_key = f"otp_{user.id}"
        cached_otp = cache.get(cache_key)
        if cached_otp is not None:
            return Response(
            {'detail': 'An active OTP already exists. Please wait or use it.'},
            status=status.HTTP_400_BAD_REQUEST
            )

        otp = ''.join(random.choices(string.digits, k=6))
        send_mail(
            'Password Reset OTP',
            f'Your OTP for password reset is: {otp}',
            settings.DEFAULT_FROM_EMAIL,
            [email],fail_silently=False
        )
        user.info.otp = otp
        user.info.save()
        # Store OTP in cache with 60s expiry (key: "otp_{user_id}")
        cache_key = f"otp_{user.id}"
        cache.set(cache_key, otp, 60)  # 60 seconds = 1 minute

        
        return Response({'detail': 'OTP sent to your email.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], authentication_classes=[])
    def reset_password(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
    
        try:
            user_info = UserInfo.objects.get(otp=otp)
        except UserInfo.DoesNotExist:
            return Response(
                {'detail': 'Invalid OTP.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if OTP is expired (cache is cleared)
        cache_key = f"otp_{user_info.user.id}"
        cached_otp = cache.get(cache_key)
        if cached_otp is None:
        # OTP expired → Clear it from DB
            user_info.otp = ''
            user_info.save()
            return Response(
                {'detail': 'OTP expired. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
        )
        user = user_info.user
        user.set_password(new_password)
        user.save()

        user_info.otp = ''
        user_info.save()
        
        return Response({'detail': 'Password reset successful.'}, status=status.HTTP_200_OK)