from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.utils import validate_password_strength

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'phone', 'is_active', 'date_joined', 'last_login']


    def validate_password(self, value):
        is_valid, errors = validate_password_strength(value)
        if not is_valid:
            raise serializers.ValidationError(errors[0])
        return value


    def update(self, instance, validated_data):
        password = validated_data.get('password')
        if password:
            is_valid, errors = validate_password_strength(password)
            if not is_valid:
                raise serializers.ValidationError(errors[0])
            instance.set_password(password)
        return super().update(validated_data)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True, min_length=3, max_length=150)
    password = serializers.CharField(required=True, min_length=8, write_only=True)
    password_confirm = serializers.CharField(required=True, write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        
        is_valid, errors = validate_password_strength(data['password'])
        if not is_valid:
            raise serializers.ValidationError(errors[0])
        
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already registered")
        
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError("Username already taken")
        
        return data


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
