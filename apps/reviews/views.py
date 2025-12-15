from rest_framework import generics, permissions, serializers
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from apps.apartments.models import Apartment
from .models import Review
from .serializers import ReviewSerializer


class ReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Review.objects.none()

    def get_queryset(self):
        apartment_id = self.kwargs["apartment_id"]
        return Review.objects.filter(apartment_id=apartment_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["apartment_id"] = self.kwargs["apartment_id"]  # FIX
        return context

    @swagger_auto_schema(responses={200: ReviewSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=ReviewSerializer,
        responses={201: ReviewSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        apartment_id = self.kwargs["apartment_id"]
        apartment = Apartment.objects.get(id=apartment_id)

        # Prevent duplicate review by same user
        if Review.objects.filter(user=self.request.user, apartment=apartment).exists():
            raise serializers.ValidationError(
                {"detail": "You already reviewed this apartment."}
            )

        serializer.save(user=self.request.user, apartment=apartment)


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = "pk"

    @swagger_auto_schema(responses={200: ReviewSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=ReviewSerializer,
        responses={200: ReviewSerializer}
    )
    def put(self, request, *args, **kwargs):
        review = self.get_object()

        if review.user != request.user:
            return Response({"error": "Not allowed"}, status=403)

        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(responses={204: "Deleted"})
    def delete(self, request, *args, **kwargs):
        review = self.get_object()

        if review.user != request.user:
            return Response({"error": "Not allowed"}, status=403)

        return super().delete(request, *args, **kwargs)
