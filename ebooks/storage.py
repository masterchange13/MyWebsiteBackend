from pathlib import Path
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.functional import cached_property


class EbookStorage(FileSystemStorage):
    @cached_property
    def base_location(self):
        return self._location or settings.MEDIA_ROOT or str(Path(settings.BASE_DIR) / 'media')

    def url(self, name):
        raise ValueError('电子书必须通过已登录的下载接口访问。')
