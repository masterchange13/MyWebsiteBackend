from django.urls import path
from video import views

urlpatterns = [
    path('video/status/', views.video_status, name='video-status'),
    path('video_feed', views.video_feed),
    path('video_feed/', views.video_feed, name='video-feed'),
]
