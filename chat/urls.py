from django.urls import path
from chat import views

urlpatten = [
    path('getUsers', views.get_users),
    path('getHistory', views.get_history),
]
