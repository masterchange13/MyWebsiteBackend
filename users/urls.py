from django.urls import path
from users import views

urlpatten = [
        path('login/', views.login),
        path('logout/', views.logout),
        path('test/', views.test),
        path('getAllNavigators/', views.get_all_navigators),
        path('save_icon/', views.save_icon),
        path('add_icon/', views.add_icon),
        path('update_icon/', views.update_icon),
        path('update_navigator_order/', views.update_navigator_order),
        path('remove_icon/', views.remove_icon),
        path('me/', views.get_me),
        path('detail/<int:user_id>/', views.get_user_detail),
        path('detail', views.get_user_detail),
        path('detail/', views.get_user_detail),
        path('register/', views.register),
        path('assignAdminOwner/', views.assign_admin_owner),
]
