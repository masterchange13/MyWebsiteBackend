from django.urls import path
from document import views

urlpatten = [
        path('publish/', views.publish),
        path('getAll/', views.get_all),
        path('detail/<int:document_id>/', views.detail),
        path('detail/', views.detail),
        path('remove/<int:document_id>/', views.remove),
        # comments
        path('comment/add/', views.add_comment),
        path('comment/list/', views.get_comments),
        path('comment/delete/<int:comment_id>/', views.delete_comment),
]
