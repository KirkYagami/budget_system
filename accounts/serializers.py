from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User


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


class CustomTokenSerializer(TokenObtainPairSerializer):
    """JWT token that includes user info in the response."""

    def validate(self, attrs):
        data  = super().validate(attrs)
        user  = self.user
        data['user'] = {
            'id':         user.id,
            'username':   user.username,
            'email':      user.email,
            'full_name':  user.get_full_name(),
            'role':       user.role,
            'department': user.department,
        }
        return data
