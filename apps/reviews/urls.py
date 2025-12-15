from django.urls import path
from .views import (
    ReviewListCreateView,
    ReviewDetailView
)

urlpatterns = [
    path('<int:apartment_id>/reviews/', ReviewListCreateView.as_view(), name="review-list-create"),
    path('reviews/<int:pk>/', ReviewDetailView.as_view(), name="review-detail"),
]
