"""Read-only system metrics selected for the backend host's platform."""
import glob
import logging
import math
import ntpath
import os
import platform
import socket
import time

from django.conf import settings

logger = logging.getLogger(__name__)
PLATFORM_LABELS = {'windows': 'Windows', 'linux': 'Linux', 'raspberrypi': '树莓派 Linux'}


def _read_text(path):
    try:
        with open(path, encoding='utf-8') as source:
            return source.read().strip().strip('\x00')
    except (OSError, UnicodeError):
        return ''


def _platform_info():
    system = platform.system()
    model = ''
    if system == 'Linux':
        model = (_read_text('/proc/device-tree/model') or
                 _read_text('/sys/firmware/devicetree/base/model'))
    detected = 'raspberrypi' if 'raspberry pi' in model.lower() else system.lower()
    configured = str(getattr(settings, 'SYSTEM_MONITOR_PLATFORM', 'auto')).strip().lower()
    warnings = []
    if configured not in ('auto', *PLATFORM_LABELS):
        warnings.append('监控平台设置无效，已恢复自动识别。')
        configured = 'auto'
    collector = detected if configured == 'auto' else configured
    if configured != 'auto' and (
        (collector == 'windows' and system != 'Windows') or
        (collector in ('linux', 'raspberrypi') and system != 'Linux')
    ):
        warnings.append('监控平台设置与服务器系统不符，已使用自动识别结果。')
        collector = detected
    return {
        'mode': configured, 'detected': detected, 'collector': collector,
        'label': PLATFORM_LABELS.get(collector, system), 'system': system,
        'release': platform.release(), 'machine': platform.machine(), 'model': model,
    }, warnings


def _disk_path(system):
    configured = getattr(settings, 'SYSTEM_MONITOR_DISK_PATH', '')
    if configured:
        return configured
    if system == 'Windows':
        drive = os.environ.get('SystemDrive') or ntpath.splitdrive(os.getcwd())[0] or 'C:'
        return drive.rstrip('\\/') + '\\'
    return '/'


def _valid_temperature(value):
    return value is not None and math.isfinite(value) and -20 <= value <= 150


def _thermal_temperature(collector):
    zones = sorted(glob.glob('/sys/class/thermal/thermal_zone*'))
    if collector == 'raspberrypi' and '/sys/class/thermal/thermal_zone0' not in zones:
        zones.insert(0, '/sys/class/thermal/thermal_zone0')
    for zone in zones:
        kind = _read_text(zone + '/type').lower()
        if not any(name in kind for name in ('cpu', 'soc', 'x86_pkg')):
            continue
        try:
            value = float(_read_text(zone + '/temp')) / 1000
        except ValueError:
            continue
        if _valid_temperature(value):
            return round(value, 1), 'thermal_zone'
    return None, None


def _get_temperature(psutil, collector):
    if collector == 'windows':
        return None, None
    if collector == 'raspberrypi':
        value, source = _thermal_temperature(collector)
        if value is not None:
            return value, source
    try:
        sensors = getattr(psutil, 'sensors_temperatures', lambda: {})() or {}
    except (OSError, AttributeError, NotImplementedError):
        sensors = {}
    for name, entries in sensors.items():
        if not any(cpu_name in name.lower() for cpu_name in ('cpu', 'coretemp', 'k10temp', 'zenpower')):
            continue
        for entry in entries:
            if _valid_temperature(entry.current):
                return round(entry.current, 1), 'psutil'
    return _thermal_temperature(collector)


def get_system_status():
    try:
        import psutil
    except ImportError:
        return None

    info, warnings = _platform_info()
    mount = _disk_path(info['system'])
    result = {
        'hostname': None, 'platform': info['system'], 'platform_info': info,
        'warnings': warnings, 'boot_time': None, 'uptime_seconds': None,
        'cpu': {'percent': None, 'core_count': None, 'freq_mhz': None, 'per_core': None, 'load': None},
        'memory': {'total': None, 'used': None, 'available': None, 'percent': None},
        'disk': {'total': None, 'used': None, 'free': None, 'percent': None, 'mount': mount},
        'temperature': {'cpu_celsius': None, 'source': None},
        'network': {'bytes_sent': None, 'bytes_recv': None, 'interfaces': []},
    }

    def sample(label, collect):
        try:
            collect()
        except Exception:
            # Unsupported or inaccessible metrics must not hide the remaining data.
            logger.warning('System monitor metric failed: %s', label, exc_info=True)
            warnings.append(f'{label}暂时无法采集，其余指标仍正常显示。')

    def host():
        result['hostname'] = socket.gethostname()
        boot = psutil.boot_time()
        result['boot_time'] = boot
        result['uptime_seconds'] = max(0, int(time.time() - boot))

    def cpu_usage():
        # Non-blocking first samples return 0; sample briefly on each request thread.
        values = psutil.cpu_percent(interval=0.1, percpu=True)
        result['cpu']['per_core'] = [round(value, 1) for value in values]
        result['cpu']['percent'] = round(sum(values) / len(values), 1) if values else None

    def cpu_count():
        result['cpu']['core_count'] = psutil.cpu_count()

    def cpu_frequency():
        frequency = psutil.cpu_freq()
        if frequency and frequency.current is not None:
            result['cpu']['freq_mhz'] = int(frequency.current)

    def load():
        if info['system'] != 'Windows' and hasattr(os, 'getloadavg'):
            result['cpu']['load'] = [round(value, 2) for value in os.getloadavg()]

    def memory():
        value = psutil.virtual_memory()
        result['memory'] = {'total': value.total, 'used': value.used,
                            'available': value.available, 'percent': round(value.percent, 1)}

    def disk():
        value = psutil.disk_usage(mount)
        result['disk'] = {'total': value.total, 'used': value.used, 'free': value.free,
                          'percent': round(value.percent, 1), 'mount': mount}

    def temperature():
        value, source = _get_temperature(psutil, info['collector'])
        result['temperature'] = {'cpu_celsius': value, 'source': source}

    def network_counters():
        value = psutil.net_io_counters()
        if value:
            result['network'].update(bytes_sent=value.bytes_sent, bytes_recv=value.bytes_recv)

    def interfaces():
        for name, addresses in psutil.net_if_addrs().items():
            for address in addresses:
                if address.family == socket.AF_INET and not address.address.startswith('127.'):
                    result['network']['interfaces'].append({'name': name, 'address': address.address})

    for label, collect in (
        ('主机信息', host), ('CPU 使用率', cpu_usage), ('CPU 核心数', cpu_count),
        ('CPU 频率', cpu_frequency), ('平均负载', load), ('内存', memory),
        ('磁盘', disk), ('CPU 温度', temperature), ('网络流量', network_counters),
        ('网络地址', interfaces),
    ):
        sample(label, collect)
    return result
