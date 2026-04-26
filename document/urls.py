from django.urls import path
from document import views

urlpatten = [
        path('publish/', views.publish),
        path('getAll/', views.get_all),
        path('detail/<int:document_id>/', views.detail),
        path('detail/', views.detail),
        path('remove/<int:document_id>/', views.remove),
]
