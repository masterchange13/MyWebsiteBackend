from django.urls import path
from document import views

urlpatten = [
        path('publish/', views.publish),
        path('getAll/', views.get_all),
]