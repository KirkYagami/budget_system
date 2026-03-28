from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User

# Roles that only an admin can assign
ELEVATED_ROLES = {'finance', 'budget_owner', 'admin'}


class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Confirm Password")

    class Meta:
        model  = User
        fields = ['username', 'email', 'first_name', 'last_name',
                  'role', 'department', 'manager', 'phone', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data.pop('password2'):
            raise serializers.ValidationError({"password": "Passwords do not match."})

        # Security: only admins can self-assign elevated roles
        requested_role = data.get('role', User.Role.EMPLOYEE)
        request = self.context.get('request')
        is_admin = request and request.user.is_authenticated and request.user.role in ('admin',)
        is_superuser = request and request.user.is_authenticated and request.user.is_superuser

        if requested_role in ELEVATED_ROLES and not (is_admin or is_superuser):
            raise serializers.ValidationError({
                "role": f"You cannot self-assign the '{requested_role}' role. Contact an admin."
            })

        return data

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'department', 'manager', 'manager_name', 'phone', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def get_manager_name(self, obj):
        return str(obj.manager) if obj.manager else None


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Admin-only serializer — can update role and all fields."""
    class Meta:
        model  = User
        fields = ['email', 'first_name', 'last_name', 'role',
                  'department', 'manager', 'phone', 'is_active']


class CustomTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['user'] = {
            'id':         user.id,
            'username':   user.username,
            'email':      user.email,
            'full_name':  user.get_full_name(),
            'role':       user.role,
            'department': user.department,
        }
        return data
