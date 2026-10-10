import asyncio
import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.apps import apps
from django.test import AsyncRequestFactory, SimpleTestCase, override_settings
from django.urls import resolve

from video import camera, views as video_views

OPTIONS = {'backend': 'auto', 'device': 'auto', 'width': 640, 'height': 480, 'fps': 30}


class DeviceSelectionTests(SimpleTestCase):
    def setUp(self):
        self.cv2 = SimpleNamespace(**{name: index for index, name in enumerate([
            'CAP_DSHOW', 'CAP_MSMF', 'CAP_ANY', 'CAP_V4L2', 'CAP_AVFOUNDATION',
            'CAP_PROP_FRAME_WIDTH', 'CAP_PROP_FRAME_HEIGHT', 'CAP_PROP_FPS', 'IMWRITE_JPEG_QUALITY',
        ])})
        self.cv2.VideoCapture = Mock()
        self.cv2.imencode = Mock(return_value=(True, SimpleNamespace(tobytes=lambda: b'jpeg')))
        modules = patch.dict(sys.modules, {'cv2': self.cv2})
        modules.start()
        self.addCleanup(modules.stop)

    def capture(self, opened=True, readable=True):
        return Mock(isOpened=Mock(return_value=opened), read=Mock(return_value=(readable, object())))

    @patch.object(camera.platform, 'system', return_value='Windows')
    def test_windows_falls_back_to_media_foundation(self, _):
        unavailable, usable = self.capture(False), self.capture()
        self.cv2.VideoCapture.side_effect = [unavailable, usable]
        adapter, frame, info = camera._open_opencv(OPTIONS)
        self.addCleanup(adapter.close)
        self.assertEqual(frame, b'jpeg')
        self.assertEqual(info['device'], '0')
        self.assertEqual(self.cv2.VideoCapture.call_args_list[1].args, (0, self.cv2.CAP_MSMF))
        unavailable.release.assert_called_once()

    @patch.object(camera.platform, 'system', return_value='Windows')
    def test_driver_exception_does_not_prevent_next_backend(self, _):
        self.cv2.VideoCapture.side_effect = [RuntimeError('driver failure'), self.capture()]
        adapter, _, _ = camera._open_opencv(OPTIONS)
        adapter.close()
        self.assertEqual(self.cv2.VideoCapture.call_count, 2)

    @patch.object(camera.platform, 'system', return_value='Linux')
    def test_linux_skips_unreadable_video_node(self, _):
        bad, good = self.capture(readable=False), self.capture()
        self.cv2.VideoCapture.side_effect = [bad, good]
        with patch.object(camera.glob, 'glob', side_effect=[[], ['/dev/video0', '/dev/video2']]):
            adapter, _, info = camera._open_opencv(OPTIONS)
        adapter.close()
        self.assertEqual(info['device'], '/dev/video2')
        self.assertEqual(self.cv2.VideoCapture.call_args.args, ('/dev/video2', self.cv2.CAP_V4L2))
        bad.release.assert_called_once()

    @patch.object(camera.platform, 'system', return_value='Linux')
    def test_no_camera_returns_actionable_message(self, _):
        with patch.object(camera.glob, 'glob', return_value=[]):
            with self.assertRaisesMessage(camera.CameraError, '未检测到摄像头'):
                camera._open_opencv(OPTIONS)
        self.cv2.VideoCapture.assert_not_called()

    @patch.object(camera.platform, 'system', return_value='Linux')
    def test_explicit_device_is_not_replaced_by_other_camera(self, _):
        self.cv2.VideoCapture.return_value = self.capture(False)
        with self.assertRaises(camera.CameraError):
            camera._open_opencv({**OPTIONS, 'device': '/dev/video9'})
        self.cv2.VideoCapture.assert_called_once_with('/dev/video9', self.cv2.CAP_V4L2)
        self.cv2.VideoCapture.return_value.release.assert_called_once()

    @patch.object(camera.platform, 'system', return_value='Darwin')
    def test_mac_uses_avfoundation(self, _):
        self.cv2.VideoCapture.return_value = self.capture()
        adapter, _, _ = camera._open_opencv({**OPTIONS, 'device': '1'})
        adapter.close()
        self.cv2.VideoCapture.assert_called_once_with(1, self.cv2.CAP_AVFOUNDATION)

    @patch.object(camera.platform, 'system', return_value='Linux')
    @patch.object(camera.platform, 'machine', return_value='aarch64')
    def test_arm_linux_falls_back_from_csi_to_usb(self, *_):
        with patch.object(camera, '_open_pi', side_effect=camera.CameraError('no CSI')), \
                patch.object(camera, '_open_opencv', return_value='usb') as usb:
            self.assertEqual(camera.open_camera(OPTIONS), 'usb')
        usb.assert_called_once()

    def test_explicit_csi_does_not_silently_select_usb(self):
        with patch.object(camera, '_open_pi', side_effect=camera.CameraError('no CSI')), \
                patch.object(camera, '_open_opencv') as usb:
            with self.assertRaisesMessage(camera.CameraError, 'no CSI'):
                camera.open_camera({**OPTIONS, 'device': 'csi:1'})
        usb.assert_not_called()

    @patch.object(camera.platform, 'system', return_value='Linux')
    def test_picamera_reports_no_connected_camera(self, _):
        pi = Mock(global_camera_info=Mock(return_value=[]))
        with patch.dict(sys.modules, {'picamera2': SimpleNamespace(Picamera2=pi)}):
            with self.assertRaisesMessage(camera.CameraError, '未检测到树莓派摄像头'):
                camera._open_pi(OPTIONS)
        pi.assert_not_called()

    @patch.object(camera.platform, 'system', return_value='Linux')
    def test_picamera_configures_and_encodes_first_frame(self, _):
        device = Mock()
        device.capture_file.side_effect = lambda output, format: output.write(b'pi-jpeg')
        pi = Mock(return_value=device, global_camera_info=Mock(return_value=[{}]))
        with patch.dict(sys.modules, {'picamera2': SimpleNamespace(Picamera2=pi)}):
            adapter, frame, info = camera._open_pi(OPTIONS)
        self.assertEqual(frame, b'pi-jpeg')
        self.assertEqual(info['device'], 'csi:0')
        device.create_video_configuration.assert_called_once_with(
            main={'size': (640, 480)}, controls={'FrameRate': 30}, buffer_count=4,
        )
        adapter.close()
        device.stop.assert_called_once()
        device.close.assert_called_once()


@override_settings(VIDEO_CAMERA_FPS=30)
class CameraLifecycleTests(SimpleTestCase):
    def manager(self, **kwargs):
        self.device = Mock(read=Mock(return_value=b'next-jpeg'))
        self.opener = Mock(return_value=(self.device, b'first-jpeg', {'backend': 'opencv', 'device': '0'}))
        manager = camera.CameraManager(opener=self.opener, **kwargs)
        self.addCleanup(manager.close)
        return manager

    def test_two_viewers_share_capture_and_disconnect_independently(self):
        manager = self.manager()
        manager.prepare()
        first, second = camera.stream_frames(manager), camera.stream_frames(manager)
        self.addCleanup(first.close)
        self.addCleanup(second.close)
        self.assertIn(b'Content-Type: image/jpeg', next(first))
        self.assertIn(b'jpeg', next(second))
        self.assertEqual(manager.clients, 2)
        manager.prepare()
        self.opener.assert_called_once()
        first.close()
        self.assertEqual(manager.clients, 1)
        second.close()
        self.assertEqual(manager.clients, 0)

    def test_idle_camera_is_released_and_reconnects(self):
        manager = self.manager(idle_seconds=0.04)
        manager.prepare()
        with manager.condition:
            self.assertTrue(manager.condition.wait_for(lambda: manager.thread is None, timeout=1))
        self.device.close.assert_called_once()
        manager.prepare()
        self.assertEqual(self.opener.call_count, 2)

    def test_capture_failure_ends_stream_and_health_does_not_reopen(self):
        manager = self.manager()
        self.device.read.side_effect = camera.CameraError('device unplugged')
        with self.assertLogs('video.camera', level='WARNING'):
            manager.prepare()
            stream = camera.stream_frames(manager)
            next(stream)
            with manager.condition:
                self.assertTrue(manager.condition.wait_for(lambda: bool(manager.error), timeout=1))
        self.assertEqual(list(stream), [])
        self.assertEqual(manager.clients, 0)
        with self.assertRaisesMessage(camera.CameraError, 'device unplugged'):
            manager.inspect()
        self.opener.assert_called_once()

    def test_slow_open_has_bounded_wait(self):
        gate = threading.Event()
        manager = self.manager()
        def delayed_open(options):
            gate.wait(1)
            return self.device, b'jpeg', {}

        self.opener.side_effect = delayed_open
        try:
            with self.assertRaisesMessage(camera.CameraError, '等待摄像头画面超时'):
                manager.prepare(timeout=0.01)
        finally:
            gate.set()

    async def test_async_stream_releases_subscription_on_close(self):
        manager = Mock(wait_frame=Mock(return_value=(1, b'jpeg')))
        stream = camera.async_stream_frames(manager)
        self.assertIn(b'jpeg', await anext(stream))
        await stream.aclose()
        manager.subscribe.assert_called_once()
        manager.unsubscribe.assert_called_once()

    async def test_async_stream_releases_subscription_on_cancel(self):
        gate = threading.Event()
        entered = threading.Event()

        def wait_frame(previous):
            entered.set()
            gate.wait(1)
            return 1, b'jpeg'

        manager = Mock(wait_frame=wait_frame)
        stream = camera.async_stream_frames(manager)
        task = asyncio.create_task(anext(stream))
        try:
            await asyncio.to_thread(entered.wait, 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        finally:
            gate.set()
            await stream.aclose()
        manager.unsubscribe.assert_called_once()


@override_settings(ROOT_URLCONF='video.urls')
class VideoEndpointTests(SimpleTestCase):
    def setUp(self):
        for target, value in [('_get_request_user', Mock(return_value=object())), ('camera_manager', Mock())]:
            patcher = patch.object(video_views, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    @override_settings(ROOT_URLCONF='MyWebsiteBackend.urls')
    def test_app_registration_and_production_routes(self):
        self.assertEqual(apps.get_app_config('video').name, 'video')
        self.assertIs(resolve('/video/status/').func, video_views.video_status)
        self.assertIs(resolve('/video_feed/').func, video_views.video_feed)

    def test_endpoints_require_login_without_opening_camera(self):
        with patch.object(video_views, '_get_request_user', return_value=None):
            for url in ['/video/status/', '/video_feed', '/video_feed/']:
                self.assertEqual(self.client.get(url).status_code, 401)
        video_views.camera_manager.prepare.assert_not_called()

    def test_no_camera_returns_json_instead_of_stream(self):
        video_views.camera_manager.prepare.side_effect = camera.CameraError('未检测到摄像头，请连接后重试。')
        for url in ['/video/status/', '/video_feed/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 503)
            self.assertIn('未检测到摄像头', response.json()['message'])

    def test_health_check_only_inspects_existing_capture(self):
        video_views.camera_manager.inspect.return_value = {'device': '0', 'platform': 'Windows'}
        self.assertEqual(self.client.get('/video/status/?check_only=1').json()['data']['device'], '0')
        video_views.camera_manager.prepare.assert_not_called()

    def test_wsgi_stream_headers_and_route_alias(self):
        for url in ['/video_feed', '/video_feed/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.is_async)
            self.assertEqual(response['X-Accel-Buffering'], 'no')
            self.assertIn('boundary=frame', response['Content-Type'])
            response.close()

    async def test_asgi_uses_async_iterator_and_valid_multipart_frames(self):
        video_views.camera_manager.wait_frame.return_value = (1, b'jpeg')
        response = video_views.video_feed(AsyncRequestFactory().get('/video_feed/'))
        self.assertTrue(response.is_async)
        self.assertEqual(await anext(response._iterator), camera.multipart_frame(b'jpeg'))
        await response._iterator.aclose()
        video_views.camera_manager.unsubscribe.assert_called_once()

    def test_post_is_rejected(self):
        self.assertEqual(self.client.post('/video/status/').status_code, 405)
        video_views.camera_manager.prepare.assert_not_called()
