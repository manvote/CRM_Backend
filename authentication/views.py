import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.mail import send_mail

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from .models import PasswordResetToken
from .serializers import (
    SignupSerializer,
    LoginSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)

class SignupAPIView(APIView):

    @extend_schema(request=SignupSerializer, tags=["Authentication"])
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "User registered successfully"},
            status=status.HTTP_201_CREATED
        )

class LoginAPIView(APIView):

    @extend_schema(request=LoginSerializer, tags=["Authentication"])
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        user = authenticate(
            username=user_obj.username,
            password=password
        )

        if not user:
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": "Admin" if user.is_superuser else "User",
                },
            }
        )
        

class ForgotPasswordAPIView(APIView):

    @extend_schema(request=ForgotPasswordSerializer, tags=["Authentication"])
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        token = uuid.uuid4().hex
        expires_at = timezone.now() + timedelta(minutes=15)

        PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )

        reset_link = f"http://localhost:3000/reset-password?token={token}"

        send_mail(
            subject="Reset Your Password",
            message=f"Click the link to reset your password:\n{reset_link}",
            from_email="noreply@crm.com",
            recipient_list=[email],
        )

        return Response(
            {"detail": "Password reset link sent"},
            status=status.HTTP_200_OK
        )

class ResetPasswordAPIView(APIView):

    @extend_schema(request=ResetPasswordSerializer, tags=["Authentication"])
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            reset_token = PasswordResetToken.objects.get(token=token)
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"detail": "Invalid token"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if reset_token.is_expired():
            reset_token.delete()
            return Response(
                {"detail": "Token expired"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = reset_token.user
        user.set_password(new_password)
        user.save()

        reset_token.delete()

        return Response(
            {"detail": "Password reset successful"},
            status=status.HTTP_200_OK
        )
