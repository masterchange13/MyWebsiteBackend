from django.db import models

class ToDoList(models.Model):
    """Model definition for ToDoListModel."""

    # TODO: Define fields here
    title = models.TextField()
    completed = models.BooleanField(default=False)
    # description = models.TextField()  
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)
