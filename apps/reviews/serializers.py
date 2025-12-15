from rest_framework import serializers
from .models import Review
from rest_framework import serializers
from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'apartment', 'user', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'user', 'apartment', 'created_at']

    def validate(self, attrs):
        user = self.context['request'].user
        apartment = self.context['apartment_id']

        if Review.objects.filter(user=user, apartment=apartment).exists():
            raise serializers.ValidationError(
                "You have already submitted a review for this apartment."
            )

        return attrs
