from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('users', '0009_app_launcher')]

    operations = [
        migrations.AddField(
            model_name='user', name='can_use_terminal',
            field=models.BooleanField(
                default=False, verbose_name='终端权限',
                help_text='允许此网站账号连接服务器终端，命令以运行后端的系统账号身份执行。',
            ),
        ),
    ]
