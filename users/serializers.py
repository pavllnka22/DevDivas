import random

from django.core.mail import send_mail
from rest_framework import serializers
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.core.validators import validate_email
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

CustomUser = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_check = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = [ 'first_name', 'last_name', 'email', 'phone', 'password', 'password_check']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_email(self, value):

        validate_email(value)
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate(self, data):

        password1 = data.get('password')
        password2 = data.get('password_check')

        if password1 != password2:
            raise serializers.ValidationError({"password2": "passwords don't match."})

        if len(password1) < 8:
            raise serializers.ValidationError({"password1": "password should be at least 8 characters."})

        if not any(char.isdigit() for char in password1):
            raise serializers.ValidationError({"password1": "password should contain at least one number."})

        return data

    def create(self, validated_data):

        validated_data.pop('password_check')
        password = validated_data.pop('password')
        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)

        code = str(random.randint(100000, 999999))
        user.email_verification_code = code
        user.save()

        send_mail(
            subject="Finish your registration in one step. Do not share your verification code with anyone",
            message=f"Your code: {code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        email = attrs.get('email') or attrs.get('username')  # фронт може прислати email
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError({'non_field_errors': ['Email and password required']})

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({'non_field_errors': ['Invalid email or password']})

        if not user.check_password(password):
            raise serializers.ValidationError({'non_field_errors': ['Invalid email or password']})

        if not user.is_active:
            raise serializers.ValidationError({'non_field_errors': ['User account is disabled.']})

        self.user = user
        data = super().validate({'username': user.get_username(), 'password': password})
        data['user'] = {
            'id': user.id,
            'email': user.email,
            'first_name': getattr(user, 'first_name', ''),
            'last_name': getattr(user, 'last_name', ''),
        }
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer