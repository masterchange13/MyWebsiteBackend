from django.urls import path
from decisionHelper import views

urlpatterns = [
    path('record/', views.record_decision),
    path('history/', views.get_history),
    path('clear/', views.clear_history),
]
