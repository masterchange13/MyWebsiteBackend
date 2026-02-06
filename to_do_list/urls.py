from django.urls import path
from to_do_list import views

urlpatten = [
        # to do list
        path('list', views.get_to_do_list),
        path('add', views.add_to_do_list),
        path('update', views.update_to_do_list),
        path('remove', views.remove_to_do_list),
        path('getAll', views.get_all_to_do_list),
        path('updateTodoStatus', views.update_to_do_status),
        path('doneEdit', views.done_edit),
        path('removeCompleted', views.remove_completed),
]