import json
import socket
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from config import system_status as monitor
from config import views


@override_settings(SYSTEM_MONITOR_PLATFORM='auto', SYSTEM_MONITOR_DISK_PATH='')
class SystemMonitorTests(SimpleTestCase):
    def setUp(self):
        self.psutil = SimpleNamespace(
            boot_time=Mock(return_value=1000),
            cpu_percent=Mock(return_value=[10, 30]),
            cpu_count=Mock(return_value=2),
            cpu_freq=Mock(return_value=SimpleNamespace(current=1500)),
            virtual_memory=Mock(return_value=SimpleNamespace(total=100, used=40, available=60, percent=40)),
            disk_usage=Mock(return_value=SimpleNamespace(total=1000, used=200, free=800, percent=20)),
            sensors_temperatures=Mock(return_value={}),
            net_io_counters=Mock(return_value=SimpleNamespace(bytes_sent=100, bytes_recv=200)),
            net_if_addrs=Mock(return_value={'eth0': [SimpleNamespace(family=socket.AF_INET, address='192.168.1.10')]}),
        )
        self.modules = patch.dict(sys.modules, {'psutil': self.psutil})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.files = patch.object(monitor, '_read_text', return_value='')
        self.files.start()
        self.addCleanup(self.files.stop)
        self.zones = patch.object(monitor.glob, 'glob', return_value=[])
        self.zones.start()
        self.addCleanup(self.zones.stop)

    @patch.object(monitor.platform, 'system', return_value='Windows')
    def test_windows_detects_host_and_system_drive(self, _):
        with patch.dict(monitor.os.environ, {'SystemDrive': 'D:'}):
            result = monitor.get_system_status()
        self.assertEqual(result['platform_info']['collector'], 'windows')
        self.assertEqual(result['disk']['mount'], 'D:\\')
        self.psutil.disk_usage.assert_called_once_with('D:\\')
        self.assertEqual(result['cpu']['percent'], 20)
        self.assertIsNone(result['cpu']['load'])
        self.assertIsNone(result['temperature']['cpu_celsius'])
        self.psutil.sensors_temperatures.assert_not_called()

    @patch.object(monitor.platform, 'system', return_value='Linux')
    def test_linux_reads_cpu_sensor_not_disk_temperature(self, _):
        self.psutil.sensors_temperatures.return_value = {
            'nvme': [SimpleNamespace(current=80)],
            'coretemp': [SimpleNamespace(current=52)],
        }
        with patch.object(monitor.os, 'getloadavg', return_value=(1, 2, 3), create=True):
            result = monitor.get_system_status()
        self.assertEqual(result['platform_info']['collector'], 'linux')
        self.assertEqual(result['disk']['mount'], '/')
        self.assertEqual(result['cpu']['load'], [1, 2, 3])
        self.assertEqual(result['temperature']['cpu_celsius'], 52)

    @patch.object(monitor.platform, 'system', return_value='Linux')
    def test_raspberry_pi_is_detected_and_reads_cpu_thermal_zone(self, _):
        files = {
            '/proc/device-tree/model': 'Raspberry Pi 5 Model B',
            '/sys/class/thermal/thermal_zone0/type': 'cpu-thermal',
            '/sys/class/thermal/thermal_zone0/temp': '46500',
        }
        with patch.object(monitor, '_read_text', side_effect=lambda path: files.get(path, '')):
            result = monitor.get_system_status()
        self.assertEqual(result['platform_info']['collector'], 'raspberrypi')
        self.assertEqual(result['temperature'], {'cpu_celsius': 46.5, 'source': 'thermal_zone'})

    @patch.object(monitor.platform, 'system', return_value='Linux')
    def test_metric_failure_preserves_remaining_data(self, _):
        self.psutil.cpu_freq.side_effect = RuntimeError('frequency unavailable')
        self.psutil.disk_usage.side_effect = PermissionError('access denied')
        with self.assertLogs('config.system_status', level='WARNING'):
            result = monitor.get_system_status()
        self.assertEqual(result['memory']['percent'], 40)
        self.assertEqual(result['network']['bytes_recv'], 200)
        self.assertIsNone(result['cpu']['freq_mhz'])
        self.assertIsNone(result['disk']['percent'])
        self.assertEqual(len(result['warnings']), 2)

    @override_settings(SYSTEM_MONITOR_DISK_PATH='/mnt/data')
    @patch.object(monitor.platform, 'system', return_value='Linux')
    def test_configured_partition(self, _):
        self.assertEqual(monitor.get_system_status()['disk']['mount'], '/mnt/data')
        self.psutil.disk_usage.assert_called_once_with('/mnt/data')

    @override_settings(SYSTEM_MONITOR_PLATFORM='windows')
    @patch.object(monitor.platform, 'system', return_value='Linux')
    def test_incompatible_setting_falls_back_to_detected_system(self, _):
        result = monitor.get_system_status()
        self.assertEqual(result['platform_info']['collector'], 'linux')
        self.assertTrue(result['warnings'])

    @override_settings(SYSTEM_MONITOR_PLATFORM='raspberrypi')
    @patch.object(monitor.platform, 'system', return_value='Linux')
    def test_pi_override_when_device_tree_is_unavailable(self, _):
        self.assertEqual(monitor.get_system_status()['platform_info']['collector'], 'raspberrypi')

    def test_missing_dependency_returns_no_data(self):
        with patch.dict(sys.modules, {'psutil': None}):
            self.assertIsNone(monitor.get_system_status())

    def test_missing_dependency_endpoint_has_actionable_error(self):
        request = RequestFactory().get('/system-status/')
        with patch.object(views, '_get_request_user', return_value=object()), patch.dict(sys.modules, {'psutil': None}):
            response = views.system_status(request)
        self.assertEqual(response.status_code, 503)
        self.assertIn('psutil', json.loads(response.content)['message'])

    def test_endpoint_requires_login(self):
        request = RequestFactory().get('/system-status/')
        with patch.object(views, '_get_request_user', return_value=None):
            response = views.system_status(request)
        self.assertEqual(response.status_code, 401)
        self.psutil.cpu_percent.assert_not_called()

    def test_endpoint_returns_successful_metrics(self):
        request = RequestFactory().get('/system-status/')
        with patch.object(views, '_get_request_user', return_value=object()):
            response = views.system_status(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['data']['cpu']['percent'], 20)
