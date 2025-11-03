import logging

from django.contrib.auth import authenticate, get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import RegisterSerializer, CustomUser

logger = logging.getLogger('users')

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    'user': RegisterSerializer(user).data,
                    'message': 'User registered successfully'
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': 'Enter both email and password'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_obj = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User with this email does not exist'}, status=status.HTTP_404_NOT_FOUND)

        user = authenticate(username=user_obj.username, password=password)

        if user is None:
            return Response({'error': 'Invalid password'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return Response({
            'message': f'Hello, {user.first_name}!',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })

class LogoutView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        logger.info("Logout attempt received")
        try:
            refresh = request.data['refresh']
            token = RefreshToken(refresh)
            token.blacklist()
            logger.info(f"User logged out successfully: {refresh}")
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class ProtectedAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        logger.info(f"Protected view accessed by: {request.user.first_name} {request.user.last_name}")
        return Response({
            'message': 'This is a protected view',
            'user': request.user.first_name}, status=status.HTTP_200_OK)
