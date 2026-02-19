from django.db import models
from users.models.user_model import User

class ToDoList(models.Model):
    """Model definition for ToDoListModel."""

    # TODO: Define fields here
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='todos', null=True, blank=True)
    title = models.TextField()
    completed = models.BooleanField(default=False)
    # description = models.TextField()  
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)
