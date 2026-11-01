from django.core.management.base import BaseCommand, CommandError
from users.models.user_model import User


class Command(BaseCommand):
    help = '设置已有网站账号为高级用户或普通用户，控制摄像头与终端权限。'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('level', choices=['advanced', 'normal'])

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['username'])
        except User.DoesNotExist:
            raise CommandError('网站账号不存在，请先创建账号。')
        except User.MultipleObjectsReturned:
            raise CommandError('存在同名账号，请通过 Django 管理后台按用户 ID 修改。')
        user.is_advanced = options['level'] == 'advanced'
        user.save(update_fields=['is_advanced'])
        label = '高级用户' if user.is_advanced else '普通用户'
        self.stdout.write(self.style.SUCCESS(f'{user.username}：已设置为{label}。'))
