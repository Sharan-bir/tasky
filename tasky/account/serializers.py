from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group
from rest_framework_simplejwt.tokens import RefreshToken
from account.models import User, Company, Domain, UserInfo
from django.core.exceptions import ObjectDoesNotExist
from typing import Dict, Any, Optional, Tuple
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.shortcuts import get_object_or_404

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'company_domain', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ['id', 'name', 'description','company', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInfo
        fields = [
            'id', 'first_name', 'last_name', 'phone', 'address', 'status', 'theme', 'otp',
            'profile_image', 'skills',  'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at',]

class UserSerializer(serializers.ModelSerializer):
    info = UserInfoSerializer(required=False)
    company = CompanySerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'company', 'role','domain', 'info']
        read_only_fields = ['id']

class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user_id'] = self.user.id
        data['company_id'] = self.user.company.id 
        data['company_name'] = self.user.company.name
        data['role'] = self.user.role
        data['domain'] = self.user.domain.id
        return data
    
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value: str) -> str:
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('User with this email does not exist.')
        return value

class ResetPasswordSerializer(serializers.Serializer):
    otp = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError('Passwords do not match.')
        return attrs

class RegisterCompanySerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Company
        fields = ['name', 'company_domain','image','email', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data: Dict[str, Any]) -> Company:
        try:
            name = validated_data.get('name')
            company_domain = validated_data.get('company_domain', '')
            image = validated_data.get('image', '')

            if Company.objects.filter(name=name).exists():
                raise serializers.ValidationError("Company already exists")
            
            company_data = {
                'name': name,
                'company_domain': company_domain,
                'image' : image
            }

            company = Company.objects.create(**company_data)
            domain = Domain.objects.create(name="all",company=company)
    
            user = User.objects.create_user(
                email=validated_data['email'],
                password=validated_data['password'],
                company=company,
                role = 'Company_owner',
                domain=domain
            )
        
            UserInfo.objects.update_or_create(user=user)
            return company
        
        except ObjectDoesNotExist as e:
            raise serializers.ValidationError({"detail": f"Invalid company or domain ID: {e}"})
        except Exception as e:
            raise serializers.ValidationError({"detail": f"An error occurred: {e}"})

class RegisterEmployeeSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    company = serializers.IntegerField(write_only=True, required=True)  

    class Meta:
        model = User
        fields = ['company', 'email', 'password','role','domain']  
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data: Dict[str, Any]) -> User:
        try:
            company = validated_data['company'] 
            domain = validated_data['domain']
            company_name = Company.objects.get(id=company)
            
            user = User.objects.create_user(
                email=validated_data['email'],
                password=validated_data['password'],
                company=company_name,
                role  = validated_data['role'],
                domain = domain
            )  
            UserInfo.objects.get_or_create(user=user) 

            return user
        except ObjectDoesNotExist as e:
            raise serializers.ValidationError({"detail": f"Invalid company or domain ID: {e}"})
        except Exception as e:
            raise serializers.ValidationError({"detail": f"An error occurred: {e}"})

class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        refresh = attrs.get('refresh')
        try:
            refresh_token = RefreshToken(refresh)
            access_token = str(refresh_token.access_token)
        except Exception as e:
            raise serializers.ValidationError('Invalid refresh token')

        return {
            'access': access_token,
            'refresh': refresh
        }