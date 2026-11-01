"""Video app camera capture with a bounded wait and shared MJPEG delivery."""
import asyncio
import glob
import io
import logging
import platform
import threading
import time

from django.conf import settings

logger = logging.getLogger(__name__)


class CameraError(Exception):
    pass


def _options():
    backend = str(getattr(settings, 'VIDEO_CAMERA_BACKEND', 'auto')).lower()
    device = str(getattr(settings, 'VIDEO_CAMERA_DEVICE', 'auto')).strip()
    if backend not in ('auto', 'opencv', 'picamera2'):
        raise CameraError('VIDEO_CAMERA_BACKEND 必须是 auto、opencv 或 picamera2。')
    return {
        'backend': backend, 'device': device,
        'width': max(160, min(1920, int(getattr(settings, 'VIDEO_CAMERA_WIDTH', 640)))),
        'height': max(120, min(1080, int(getattr(settings, 'VIDEO_CAMERA_HEIGHT', 480)))),
        'fps': max(1, min(30, int(getattr(settings, 'VIDEO_CAMERA_FPS', 15)))),
    }


class OpenCVCamera:
    def __init__(self, cv2, capture):
        self.cv2 = cv2
        self.capture = capture

    def read(self):
        ok, frame = self.capture.read()
        if not ok or frame is None:
            raise CameraError('摄像头无法读取画面，请检查设备编号、权限或是否被其他程序占用。')
        ok, jpeg = self.cv2.imencode('.jpg', frame, [self.cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            raise CameraError('摄像头画面编码失败。')
        return jpeg.tobytes()

    def close(self):
        self.capture.release()


class PiCamera:
    def __init__(self, camera):
        self.camera = camera

    def read(self):
        output = io.BytesIO()
        self.camera.capture_file(output, format='jpeg')
        return output.getvalue()

    def close(self):
        try:
            self.camera.stop()
        finally:
            self.camera.close()


def _open_pi(options):
    if platform.system() != 'Linux':
        raise CameraError('Picamera2 仅用于 Linux 上的树莓派摄像头，请改用 auto 或 opencv。')
    try:
        from picamera2 import Picamera2
    except ImportError as error:
        raise CameraError('缺少 Picamera2/libcamera；树莓派排线摄像头请安装 python3-picamera2，并让虚拟环境访问系统包。') from error
    device = options['device']
    try:
        index = 0 if device == 'auto' else int(device.removeprefix('csi:'))
    except ValueError as error:
        raise CameraError('树莓派摄像头设备应为 csi:0、csi:1 或数字编号。') from error
    if index < 0 or index >= len(Picamera2.global_camera_info()):
        raise CameraError(f'未检测到树莓派摄像头 {index}，请连接摄像头并检查 libcamera 是否识别设备。')
    camera = Picamera2(camera_num=index)
    adapter = PiCamera(camera)
    try:
        camera.configure(camera.create_video_configuration(
            main={'size': (options['width'], options['height'])},
            controls={'FrameRate': options['fps']},
            buffer_count=4,
        ))
        camera.start()
        return adapter, adapter.read(), {'backend': 'picamera2', 'device': f'csi:{index}'}
    except Exception:
        adapter.close()
        raise


def _open_opencv(options):
    try:
        import cv2
    except ImportError as error:
        raise CameraError('缺少 OpenCV，请安装 requirements.txt 的视频依赖；32 位树莓派可安装 python3-opencv。') from error
    system = platform.system()
    device = options['device']
    if device == 'auto':
        if system == 'Linux':
            devices = (sorted(glob.glob('/dev/v4l/by-id/*')) +
                       sorted(glob.glob('/dev/video[0-9]*')))
        else:
            devices = list(range(4))
    else:
        devices = [int(device) if device.isdecimal() else device]
    if not devices:
        raise CameraError('未检测到摄像头，请连接设备后重试；USB 摄像头请检查 /dev/video*，排线摄像头请使用 Picamera2。')
    backends = {
        'Windows': [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY],
        'Linux': [cv2.CAP_V4L2],
        'Darwin': [cv2.CAP_AVFOUNDATION],
    }.get(system, [cv2.CAP_ANY])
    for source in devices:
        for backend in backends:
            adapter = None
            try:
                capture = cv2.VideoCapture(source, backend)
                adapter = OpenCVCamera(cv2, capture)
                if capture.isOpened():
                    capture.set(cv2.CAP_PROP_FRAME_WIDTH, options['width'])
                    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, options['height'])
                    capture.set(cv2.CAP_PROP_FPS, options['fps'])
                    return adapter, adapter.read(), {'backend': 'opencv', 'device': str(source)}
            except Exception:
                logger.debug('Camera candidate failed: %s', source, exc_info=True)
            if adapter:
                adapter.close()
    raise CameraError(f'未检测到可用摄像头（已尝试 {devices}）。请连接设备后重试，并检查设备设置、摄像头权限和占用情况。')


def open_camera(options):
    use_pi = options['backend'] == 'picamera2' or options['device'].startswith('csi:')
    auto_pi = (options['backend'] == 'auto' and options['device'] == 'auto' and
               platform.system() == 'Linux' and
               platform.machine().lower() in ('aarch64', 'arm64', 'armv7l', 'armv6l'))
    failures = []
    if use_pi or auto_pi:
        try:
            return _open_pi(options)
        except Exception as error:
            if use_pi:
                raise CameraError(str(error)) from error
            failures.append(str(error))
    try:
        return _open_opencv(options)
    except CameraError as error:
        raise CameraError('；'.join(failures + [str(error)])) from error


class CameraManager:
    def __init__(self, opener=open_camera, idle_seconds=15):
        self.opener = opener
        self.idle_seconds = idle_seconds
        self.condition = threading.Condition()
        self.thread = None
        self.stop = threading.Event()
        self.frame = None
        self.sequence = 0
        self.error = ''
        self.info = {}
        self.clients = 0
        self.last_access = 0
        self.last_frame_at = 0

    def prepare(self, timeout=6):
        deadline = time.monotonic() + timeout
        with self.condition:
            self.last_access = time.monotonic()
            # Reconnect after the previous worker has finished releasing its device.
            if self.error and self.thread and self.thread.is_alive():
                if not self.condition.wait_for(lambda: self.thread is None, max(0, deadline - time.monotonic())):
                    raise CameraError('摄像头正在释放，请稍后重新连接。')
            if not self.thread or not self.thread.is_alive():
                self.frame = None
                self.error = ''
                self.info = {}
                self.stop.clear()
                self.thread = threading.Thread(target=self._capture, daemon=True, name='video-camera')
                self.thread.start()
            while self.frame is None and not self.error:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CameraError('等待摄像头画面超时，请检查设备、权限和驱动。')
                self.condition.wait(remaining)
            if self.error:
                raise CameraError(self.error)
            return {'platform': platform.system(), **self.info}

    def inspect(self):
        # Health checks must not reopen a camera behind an existing stream.
        with self.condition:
            if self.error or self.frame is None:
                raise CameraError(self.error or '摄像头未连接，请重新连接。')
            if time.monotonic() - self.last_frame_at > 6:
                raise CameraError('摄像头画面已停止更新，请检查设备连接。')
            return {'platform': platform.system(), **self.info}

    def _capture(self):
        camera = None
        try:
            options = _options()
            camera, frame, info = self.opener(options)
            with self.condition:
                self.info = {**info, 'width': options['width'], 'height': options['height'], 'fps': options['fps']}
            while not self.stop.is_set():
                tick = time.monotonic()
                with self.condition:
                    if self.clients == 0 and tick - self.last_access > self.idle_seconds:
                        self.frame = None
                        self.error = '摄像头连接已结束，请重新连接。'
                        break
                    self.frame = frame
                    self.last_frame_at = time.monotonic()
                    self.sequence += 1
                    self.condition.notify_all()
                self.stop.wait(max(0, 1 / options['fps'] - (time.monotonic() - tick)))
                if not self.stop.is_set():
                    frame = camera.read()
        except Exception as error:
            logger.warning('Camera capture failed: %s', error)
            with self.condition:
                self.error = str(error)
        finally:
            try:
                if camera:
                    camera.close()
            finally:
                with self.condition:
                    self.frame = None
                    if not self.error:
                        self.error = '摄像头连接已结束，请重新连接。'
                    self.thread = None
                    self.condition.notify_all()

    def wait_frame(self, previous, timeout=6):
        with self.condition:
            ready = self.condition.wait_for(
                lambda: self.error or (self.frame is not None and self.sequence != previous), timeout,
            )
            if self.error or not ready:
                raise CameraError(self.error or '摄像头画面读取超时。')
            return self.sequence, self.frame

    def subscribe(self):
        with self.condition:
            self.clients += 1
            self.last_access = time.monotonic()

    def unsubscribe(self):
        with self.condition:
            self.clients = max(0, self.clients - 1)
            self.last_access = time.monotonic()

    def close(self):
        self.stop.set()
        with self.condition:
            thread = self.thread
        if thread:
            thread.join(timeout=1)


def multipart_frame(frame):
    return (b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' +
            str(len(frame)).encode() + b'\r\n\r\n' + frame + b'\r\n')


def stream_frames(manager, can_stream=None):
    manager.subscribe()
    sequence = -1
    try:
        while True:
            sequence, frame = manager.wait_frame(sequence)
            if can_stream and not can_stream():
                break
            yield multipart_frame(frame)
    except CameraError:
        return
    finally:
        manager.unsubscribe()


async def async_stream_frames(manager, can_stream=None):
    manager.subscribe()
    sequence = -1
    try:
        while True:
            sequence, frame = await asyncio.to_thread(manager.wait_frame, sequence)
            if can_stream and not await can_stream():
                break
            yield multipart_frame(frame)
    except CameraError:
        return
    finally:
        manager.unsubscribe()


camera_manager = CameraManager()
