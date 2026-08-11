from django.urls import path
from emailer import views

urlpatterns = [
    path('config/', views.get_smtp_config),
    path('config/save/', views.save_smtp_config),
    path('send/', views.send_email),
    path('history/', views.get_history),
    path('history/delete/', views.delete_history),
]
