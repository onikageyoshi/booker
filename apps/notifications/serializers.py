from rest_framework import serializers


class NotificationSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    notification_type = serializers.ChoiceField(choices=[('info', 'Info'), ('warning', 'Warning'), ('alert', 'Alert')])
    is_read = serializers.BooleanField(default=False)
    created_at = serializers.DateTimeField(read_only=True)