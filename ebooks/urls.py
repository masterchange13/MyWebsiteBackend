from django.urls import path
from . import views

urlpatterns = [
    path('', views.library),
    path('<uuid:book_id>/', views.detail),
    path('<uuid:book_id>/chapters/<int:index>/', views.chapter),
    path('<uuid:book_id>/progress/', views.progress),
    path('<uuid:book_id>/file/', views.download),
]
