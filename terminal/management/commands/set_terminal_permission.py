from django.core.management.base import BaseCommand, CommandError

from users.models.user_model import User


class Command(BaseCommand):
    help = '在数据库中开通或撤销已有网站账号的终端权限。'

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
        user.can_use_terminal = not options['revoke']
        user.save(update_fields=['can_use_terminal'])
        action = '已开通' if user.can_use_terminal else '已撤销'
        self.stdout.write(self.style.SUCCESS(f'{user.username}：{action}终端权限。'))
