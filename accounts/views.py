from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import User
from .serializers import (AdminUserUpdateSerializer, CustomTokenSerializer,
                          RegisterSerializer, UserSerializer)


class RegisterView(generics.CreateAPIView):
    """
    Register a new user.
    - Anyone can register as `employee` or `manager`
    - Only admins can assign `finance`, `budget_owner`, `admin` roles
    """
    queryset           = User.objects.all()
    serializer_class   = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Register new user",
        operation_description=(
            "**Public endpoint** — no auth required.\n\n"
            "Roles `employee` and `manager` are freely assignable.\n\n"
            "Roles `finance`, `budget_owner`, `admin` require the request to be made by an existing admin."
        ),
        tags=['Auth'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer

    @swagger_auto_schema(
        operation_summary="Login (obtain JWT)",
        operation_description="Returns `access` token (8h) and `refresh` token (7 days) plus user info.",
        tags=['Auth'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(operation_summary="My Profile", responses={200: UserSerializer}, tags=['Auth'])
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @swagger_auto_schema(
        operation_summary="Update My Profile",
        operation_description="Update your own name, email, phone, department. Cannot change your own role.",
        request_body=UserSerializer,
        responses={200: UserSerializer},
        tags=['Auth'],
    )
    def patch(self, request):
        # Prevent self role-escalation via this endpoint
        data = request.data.copy()
        data.pop('role', None)
        serializer = UserSerializer(request.user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserListView(generics.ListAPIView):
    serializer_class   = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Users",
        manual_parameters=[
            openapi.Parameter('role', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              enum=[r[0] for r in User.Role.choices]),
            openapi.Parameter('department', openapi.IN_QUERY, type=openapi.TYPE_STRING),
        ],
        tags=['Auth'],
    )
    def get(self, request, *args, **kwargs):
        qs = User.objects.all().order_by('username')
        if request.query_params.get('role'):
            qs = qs.filter(role=request.query_params['role'])
        if request.query_params.get('department'):
            qs = qs.filter(department__icontains=request.query_params['department'])
        return Response(UserSerializer(qs, many=True).data)


class AdminUserUpdateView(APIView):
    """Admin-only — update any user's role, department, active status."""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="[Admin] Update Any User",
        operation_description=(
            "**Requires admin role.**\n\n"
            "Allows changing `role`, `department`, `manager`, `is_active` for any user.\n"
            "Use this to promote an employee to finance/manager/budget_owner."
        ),
        request_body=AdminUserUpdateSerializer,
        responses={200: UserSerializer, 403: "Forbidden"},
        tags=['Auth'],
    )
    def patch(self, request, pk):
        if not (request.user.role == 'admin' or request.user.is_superuser):
            return Response({"detail": "Admin access required."},
                            status=status.HTTP_403_FORBIDDEN)
        user       = generics.get_object_or_404(User, pk=pk)
        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(user).data)
