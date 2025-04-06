from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from account.views import (
    CompanyViewSet, DomainViewSet,
    UserViewSet, AuthViewSet, CustomTokenObtainPairView
)
from attendance.views import AttendanceViewSet

router = DefaultRouter()
# Account
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'domains', DomainViewSet, basename='domain')
router.register(r'users', UserViewSet, basename='user')

# Attendance
router.register(r'attendance', AttendanceViewSet, basename='attendance')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/', include([
        path('logout/', AuthViewSet.as_view({'post': 'logout'}), name='logout'),
        path('refresh/', AuthViewSet.as_view({'post': 'refresh'}), name='refresh'),
        path('forgot-password/', AuthViewSet.as_view({'post': 'forgot_password'}), name='forgot-password'),
        path('reset-password/', AuthViewSet.as_view({'post': 'reset_password'}), name='reset-password'),
    ])),
]