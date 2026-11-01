from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('users', '0010_user_can_use_terminal')]
    operations = [
        migrations.RenameField('user', 'can_use_terminal', 'is_advanced'),
        migrations.AlterField(
            model_name='user', name='is_advanced',
            field=models.BooleanField(default=False, verbose_name='高级用户',
                help_text='高级用户可使用服务器摄像头和终端；未勾选为普通用户。'),
        ),
    ]
