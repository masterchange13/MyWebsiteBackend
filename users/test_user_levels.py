import json
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from users.models.user_model import User
from video import views


class UserLevelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='level-user', email='level@example.test', password='unused')
        session = self.client.session
        session['user'] = self.user.username
        session.save()

    def test_normal_user_cannot_reach_camera_or_terminal(self):
        with patch.object(views, 'camera_manager') as manager:
            for url in ['/video/status/', '/video/status/?check_only=1', '/video_feed', '/video_feed/']:
                self.assertEqual(self.client.get(url).status_code, 403)
            manager.prepare.assert_not_called()
            manager.inspect.assert_not_called()
        self.assertEqual(self.client.get('/terminal/status/').status_code, 403)
        self.assertEqual(self.client.post('/terminal/session/').status_code, 403)
        self.assertFalse(self.client.get('/users/me/').json()['data']['is_advanced'])

    def test_command_controls_both_features_without_restart(self):
        for level, expected in [('advanced', 200), ('normal', 403)]:
            call_command('set_user_level', self.user.username, level, stdout=StringIO())
            with patch.object(views, 'camera_manager') as manager:
                manager.prepare.return_value = {}
                self.assertEqual(self.client.get('/video/status/').status_code, expected)
            self.assertEqual(self.client.get('/terminal/status/').status_code, expected)
            self.assertEqual(self.client.get('/users/me/').json()['data']['is_advanced'], level == 'advanced')

    def test_self_profile_cannot_upgrade_account(self):
        response = self.client.post('/users/update/', json.dumps({'is_advanced': True}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_advanced)

    def test_camera_stream_stops_after_downgrade(self):
        User.objects.filter(pk=self.user.pk).update(is_advanced=True)
        with patch.object(views, 'camera_manager') as manager:
            manager.wait_frame.return_value = (1, b'jpeg')
            response = self.client.get('/video_feed/')
            stream = iter(response.streaming_content)
            self.assertIn(b'jpeg', next(stream))
            User.objects.filter(pk=self.user.pk).update(is_advanced=False)
            with patch.object(views.time, 'monotonic', return_value=1e20):
                self.assertEqual(list(stream), [])
            manager.unsubscribe.assert_called_once()
            response.close()
