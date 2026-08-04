from django.contrib.auth import authenticate
from django.middleware.csrf import rotate_token
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from api.serializers import CustomUserSerializer


class LoginRateThrottle(AnonRateThrottle):
    rate = '10/minute'


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def LoginView(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({'detail': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request=request, username=username, password=password)
    if user is None:
        return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)
    redirect_map = {
        'superuser': '/admin/',
        'school_admin': '/school/',
        'student': '/library/',
        'teacher': '/library/',
    }

    return Response(
        {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': CustomUserSerializer(user).data,
            'redirect': redirect_map.get(user.role, '/login/'),
        }
    )


@api_view(['POST'])
def LogoutView(request):
    rotate_token(request)
    return Response({'detail': 'Logged out.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def MeView(request):
    return Response(CustomUserSerializer(request.user).data)
