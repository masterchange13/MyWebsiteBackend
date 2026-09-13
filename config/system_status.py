"""树莓派系统状态只读采集器。

惰性导入 psutil（见 get_system_status），缺失时返回 None，
由视图层转换为 500 信封，不影响 config 模块其他端点。
逐指标 try/except：单指标失败返回 None，不拖垮整个端点。
"""
import os
import time
import socket
import platform as _platform


def _read_thermal_zone():
    """树莓派 /sys 热区温度（毫摄氏度 → 摄氏度）。"""
    path = '/sys/class/thermal/thermal_zone0/temp'
    try:
        with open(path, 'r') as f:
            millis = float(f.read().strip())
        return millis / 1000.0
    except (OSError, ValueError):
        return None


def _get_temperature(psutil):
    temp = _read_thermal_zone()
    if temp is not None:
        return temp, 'thermal_zone'
    try:
        sensors = psutil.sensors_temperatures()
        if sensors:
            for name, entries in sensors.items():
                for entry in entries:
                    if entry.current is not None:
                        return round(entry.current, 1), 'psutil'
    except (AttributeError, OSError):
        pass
    return None, None


def _get_loadavg():
    if hasattr(os, 'getloadavg'):
        try:
            return [round(x, 2) for x in os.getloadavg()]
        except OSError:
            return None
    return None


def _get_network(psutil):
    network = {'bytes_sent': None, 'bytes_recv': None, 'interfaces': []}
    try:
        counters = psutil.net_io_counters()
        network['bytes_sent'] = counters.bytes_sent
        network['bytes_recv'] = counters.bytes_recv
    except (AttributeError, OSError):
        pass
    try:
        for name, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                    network['interfaces'].append({'name': name, 'address': addr.address})
    except (AttributeError, OSError):
        pass
    return network


def get_system_status():
    try:
        import psutil
    except ImportError:
        return None

    result = {
        'hostname': None,
        'platform': None,
        'boot_time': None,
        'uptime_seconds': None,
        'cpu': {'percent': None, 'core_count': None, 'freq_mhz': None,
                'per_core': None, 'load': None},
        'memory': {'total': None, 'used': None, 'available': None, 'percent': None},
        'disk': {'total': None, 'used': None, 'free': None, 'percent': None, 'mount': '/'},
        'temperature': {'cpu_celsius': None, 'source': None},
        'network': {'bytes_sent': None, 'bytes_recv': None, 'interfaces': []},
    }

    # 主机信息
    try:
        result['hostname'] = socket.gethostname()
    except OSError:
        pass
    result['platform'] = _platform.system()

    # 开机时间 / 运行时长
    try:
        boot = psutil.boot_time()
        result['boot_time'] = boot
        result['uptime_seconds'] = int(time.time() - boot)
    except (AttributeError, OSError):
        pass

    # CPU
    cpu = result['cpu']
    try:
        cpu['percent'] = round(psutil.cpu_percent(interval=None), 1)
    except (AttributeError, OSError):
        pass
    try:
        cpu['core_count'] = psutil.cpu_count()
    except (AttributeError, OSError):
        pass
    try:
        freq = psutil.cpu_freq()
        if freq is not None and freq.current is not None:
            cpu['freq_mhz'] = int(freq.current)
    except (AttributeError, OSError):
        pass
    try:
        cpu['per_core'] = [round(x, 1) for x in psutil.cpu_percent(interval=None, percpu=True)]
    except (AttributeError, OSError):
        pass
    cpu['load'] = _get_loadavg()

    # 内存
    try:
        mem = psutil.virtual_memory()
        result['memory'] = {
            'total': mem.total,
            'used': mem.used,
            'available': mem.available,
            'percent': round(mem.percent, 1),
        }
    except (AttributeError, OSError):
        pass

    # 磁盘
    try:
        disk = psutil.disk_usage('/')
        result['disk'] = {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': round(disk.percent, 1),
            'mount': '/',
        }
    except (AttributeError, OSError):
        pass

    # 温度
    temp, source = _get_temperature(psutil)
    result['temperature'] = {'cpu_celsius': temp, 'source': source}

    # 网络
    result['network'] = _get_network(psutil)

    return result
