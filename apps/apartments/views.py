from rest_framework import generics, permissions, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from .models import Apartment, Amenity
from .serializers import ApartmentSerializer


class ApartmentListCreateView(generics.ListCreateAPIView):
    queryset = Apartment.objects.filter(is_active=True)
    serializer_class = ApartmentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(responses={200: ApartmentSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=ApartmentSerializer,
        responses={201: ApartmentSerializer}
    )
    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        amenities_ids = data.pop("amenities", [])

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        apartment = serializer.save(host=request.user)

        # Assign amenities
        if amenities_ids:
            amenities = Amenity.objects.filter(id__in=amenities_ids)
            apartment.amenities.set(amenities)

        return Response(ApartmentSerializer(apartment).data, status=status.HTTP_201_CREATED)


class ApartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Apartment.objects.all()
    serializer_class = ApartmentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'pk'

    @swagger_auto_schema(responses={200: ApartmentSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=ApartmentSerializer,
        responses={200: ApartmentSerializer}
    )
    def put(self, request, *args, **kwargs):
        apartment = self.get_object()
        if apartment.host != request.user:
            return Response({"error": "Not allowed"}, status=403)

        data = request.data.copy()
        amenities_ids = data.pop("amenities", [])

        serializer = self.get_serializer(apartment, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        apartment = serializer.save()

        # Update amenities
        if amenities_ids:
            amenities = Amenity.objects.filter(id__in=amenities_ids)
            apartment.amenities.set(amenities)

        return Response(ApartmentSerializer(apartment).data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        apartment = self.get_object()
        if apartment.host != request.user:
            return Response({"error": "Not allowed"}, status=403)
        return super().delete(request, *args, **kwargs)
