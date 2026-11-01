from django.core.management.base import BaseCommand, CommandError

from users.models.user_model import User


class Command(BaseCommand):
    help = '兼容旧命令：设置高级/普通用户，同时控制摄像头和终端。建议使用 set_user_level。'

    def add_arguments(self, parser):
        parser.add_argument('username', help='已有网站账号的用户名')
        parser.add_argument('--revoke', action='store_true', help='撤销终端权限')

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['username'])
        except User.DoesNotExist:
            raise CommandError('网站账号不存在，请先创建账号。')
        except User.MultipleObjectsReturned:
            raise CommandError('存在同名账号，请通过 Django 管理后台按用户 ID 修改权限。')
        user.is_advanced = not options['revoke']
        user.save(update_fields=['is_advanced'])
        label = '高级用户' if user.is_advanced else '普通用户'
        self.stdout.write(self.style.SUCCESS(f'{user.username}：已设置为{label}（摄像头和终端权限同步变更）。'))
