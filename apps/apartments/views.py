from rest_framework import generics, permissions, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .models import Apartment, ApartmentImage
from .serializers import ApartmentSerializer, ApartmentImageSerializer
from .utils import upload_apartment_image  # Cloudinary upload function


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
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(host=self.request.user)


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
        return super().put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        apartment = self.get_object()
        if apartment.host != request.user:
            return Response({"error": "Not allowed"}, status=403)
        return super().delete(request, *args, **kwargs)



class ApartmentImageListCreateView(generics.ListCreateAPIView):
    serializer_class = ApartmentImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        apartment_id = self.kwargs.get('apartment_id')
        return ApartmentImage.objects.filter(apartment__id=apartment_id)

    @swagger_auto_schema(responses={200: ApartmentImageSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=ApartmentImageSerializer,
        responses={201: ApartmentImageSerializer}
    )
    def post(self, request, *args, **kwargs):
        apartment_id = self.kwargs.get('apartment_id')
        apartment = generics.get_object_or_404(Apartment, id=apartment_id)

        # Ensure only host can add images
        if apartment.host != request.user:
            return Response({"error": "Not allowed"}, status=403)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Upload image to Cloudinary
        image_file = serializer.validated_data.get('image')
        cloudinary_url = upload_apartment_image(image_file)
        serializer.save(apartment=apartment, image=cloudinary_url)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
