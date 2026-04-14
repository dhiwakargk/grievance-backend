from rest_framework import serializers
from .models import User, Department, Grievance, StatusLog

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role', 'department', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class StatusLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True, allow_null=True)
    class Meta:
        model = StatusLog
        fields = '__all__'

class GrievanceSerializer(serializers.ModelSerializer):
    logs = StatusLogSerializer(many=True, read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    assigned_user_name = serializers.CharField(source='assigned_user.username', read_only=True, allow_null=True)

    class Meta:
        model = Grievance
        fields = '__all__'
        read_only_fields = ('ai_summary', 'extracted_text', 'urgency', 'status', 'user', 'assigned_user')

class GrievanceCreateSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_blank=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = Grievance
        fields = ['title', 'description', 'image', 'latitude', 'longitude']
