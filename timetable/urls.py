from django.urls import path
from timetable import views

urlpatten = [
        # timetable
        path('list', views.get_list),
        path('add', views.add_entry),
        path('update', views.update_entry),
        path('remove', views.remove_entry),
        path('config', views.get_config),
        path('config/save', views.save_config),
]
