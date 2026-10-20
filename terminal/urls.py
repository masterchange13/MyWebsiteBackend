from django.urls import path
from . import views

urlpatterns = [
    path('status/', views.status),
    path('session/', views.create_session),
    path('session/close/', views.close_session),
]
