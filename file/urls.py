from django.urls import path
from file import views

urlpatten = [
        path('upload/', views.upload),
        path('list/', views.list_files),
        path('open/<str:filename>', views.open_file),
]
