from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import User
from .serializers import CustomTokenSerializer, RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """Register a new user account."""
    queryset         = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Register new user",
        operation_description="Create a new user with role, department, and optional manager.",
        responses={201: UserSerializer, 400: "Validation errors"},
        tags=['Auth'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Login – returns access + refresh tokens with user info."""
    serializer_class = CustomTokenSerializer

    @swagger_auto_schema(
        operation_summary="Login (obtain JWT)",
        operation_description="Returns access token (8 h) and refresh token (7 days).",
        tags=['Auth'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MeView(APIView):
    """Return the currently authenticated user's profile."""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="My Profile",
        responses={200: UserSerializer},
        tags=['Auth'],
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @swagger_auto_schema(
        operation_summary="Update My Profile",
        request_body=UserSerializer,
        responses={200: UserSerializer},
        tags=['Auth'],
    )
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserListView(generics.ListAPIView):
    """List all users (admin / finance / manager use)."""
    serializer_class   = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset           = User.objects.all().order_by('username')

    @swagger_auto_schema(
        operation_summary="List Users",
        manual_parameters=[
            openapi.Parameter('role', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              description="Filter by role", enum=[r[0] for r in User.Role.choices]),
            openapi.Parameter('department', openapi.IN_QUERY, type=openapi.TYPE_STRING),
        ],
        tags=['Auth'],
    )
    def get(self, request, *args, **kwargs):
        role       = request.query_params.get('role')
        department = request.query_params.get('department')
        qs         = self.get_queryset()
        if role:
            qs = qs.filter(role=role)
        if department:
            qs = qs.filter(department__icontains=department)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
