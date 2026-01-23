from django.urls import path
from login import views

urlpatten = [
        path('login/', views.login)
]
