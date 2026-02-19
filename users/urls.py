from django.urls import path
from users import views

urlpatten = [
        path('login/', views.login),
        path('test/', views.test),
        path('getAllNavigators/', views.get_all_navigators),
        path('save_icon/', views.save_icon),
        path('add_icon/', views.add_icon),
        path('remove_icon/', views.remove_icon),
        path('me/', views.get_me),
        path('detail/', views.get_user_detail),
        path('register/', views.register),
        path('assignAdminOwner/', views.assign_admin_owner),
]
