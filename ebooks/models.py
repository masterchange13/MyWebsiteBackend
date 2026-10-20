from pathlib import PurePosixPath
import uuid

from django.db import models
from .storage import EbookStorage


def book_path(instance, filename):
    return f'ebooks/{instance.user_id}/{instance.id}/{PurePosixPath(filename).name}'


class Ebook(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='ebooks')
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200, blank=True)
    format = models.CharField(max_length=8)
    size = models.PositiveIntegerField()
    original_name = models.CharField(max_length=255)
    file = models.FileField(upload_to=book_path, storage=EbookStorage())
    content = models.FileField(upload_to=book_path, storage=EbookStorage(), blank=True)
    chapters = models.JSONField(default=list)
    progress = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-last_read_at', '-created_at']
