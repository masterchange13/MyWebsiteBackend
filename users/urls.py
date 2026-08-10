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
        path('insert_navigator_order/', views.insert_navigator_order),
        path('swap_navigator_order/', views.swap_navigator_order),
        path('remove_icon/', views.remove_icon),
        path('me/', views.get_me),
        path('detail/<int:user_id>/', views.get_user_detail),
        path('detail', views.get_user_detail),
        path('detail/', views.get_user_detail),
        path('register/', views.register),
        path('update/', views.update_user),
        path('assignAdminOwner/', views.assign_admin_owner),
        # App Launcher
        path('getAllAppLaunchers/', views.get_all_app_launchers),
        path('save_app_launcher/', views.save_app_launcher),
        path('update_app_launcher/', views.update_app_launcher),
        path('remove_app_launcher/', views.remove_app_launcher),
        path('insert_app_launcher_order/', views.insert_app_launcher_order),
        path('swap_app_launcher_order/', views.swap_app_launcher_order),
        path('launch_app/', views.launch_app),
]
