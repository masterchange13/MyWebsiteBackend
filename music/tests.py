import tempfile
from pathlib import Path

from django.http import Http404
from django.test import AsyncRequestFactory, RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve

from music.services.audio_stream import CHUNK_SIZE, audio_response


class AudioStreamingTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        audio_dir = Path(directory.name) / 'media/music/audio'
        audio_dir.mkdir(parents=True)
        self.payload = bytes(range(256)) * 600
        (audio_dir / 'sample.mp3').write_bytes(self.payload)
        (audio_dir / 'empty.mp3').write_bytes(b'')
        self.factory = RequestFactory()

    def response(self, range_header=None, method='get', **headers):
        if range_header:
            headers['HTTP_RANGE'] = range_header
        request = getattr(self.factory, method)('/media/music/audio/sample.mp3', **headers)
        response = audio_response(request, 'sample.mp3')
        self.addCleanup(response.close)
        return response

    def body(self, response):
        return b''.join(response.streaming_content) if response.streaming else response.content

    def test_full_file_is_streamed_in_bounded_chunks(self):
        response = self.response()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Accept-Ranges'], 'bytes')
        self.assertEqual(int(response['Content-Length']), len(self.payload))
        chunks = list(response.streaming_content)
        self.assertTrue(all(len(chunk) <= CHUNK_SIZE for chunk in chunks))
        self.assertEqual(b''.join(chunks), self.payload)

    def test_seeking_returns_only_requested_bytes(self):
        # Forward and backward seeks must each return their own offset, not byte 0.
        for start, end in [(70000, 80000), (5000, 6999), (100000, 100099)]:
            response = self.response(f'bytes={start}-{end}')
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response['Content-Range'], f'bytes {start}-{end}/{len(self.payload)}')
            self.assertEqual(int(response['Content-Length']), end - start + 1)
            self.assertEqual(self.body(response), self.payload[start:end + 1])

    def test_open_ended_and_suffix_ranges(self):
        for header, expected in [('bytes=150000-', self.payload[150000:]), ('bytes=-300', self.payload[-300:])]:
            response = self.response(header)
            self.assertEqual(response.status_code, 206)
            self.assertEqual(self.body(response), expected)

    def test_end_is_clamped_to_file_length(self):
        response = self.response('bytes=100-999999')
        self.assertEqual(response.status_code, 206)
        self.assertEqual(self.body(response), self.payload[100:])

    def test_oversized_suffix_returns_whole_file_as_partial(self):
        response = self.response('bytes=-999999')
        self.assertEqual(response.status_code, 206)
        self.assertEqual(self.body(response), self.payload)

    def test_unsatisfiable_ranges_have_correct_file_size(self):
        for header in ['bytes=999999-', 'bytes=100-1', 'bytes=-0']:
            response = self.response(header)
            self.assertEqual(response.status_code, 416)
            self.assertEqual(response['Content-Range'], f'bytes */{len(self.payload)}')
            self.assertEqual(response['Content-Length'], '0')

    def test_unsupported_and_malformed_ranges_are_ignored(self):
        for header in ['items=0-5', 'bytes=abc', 'bytes=0-2,5-7', 'bytes=-', 'bytes=' + '9' * 5000 + '-']:
            response = self.response(header)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.body(response), self.payload)

    def test_head_has_full_length_but_no_body(self):
        response = self.response('bytes=100-200', method='head')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(response['Content-Length']), len(self.payload))
        self.assertEqual(self.body(response), b'')

    def test_if_range_etag_and_date_support(self):
        initial = self.response(method='head')
        for validator in [initial['ETag'], initial['Last-Modified']]:
            response = self.response('bytes=100-200', HTTP_IF_RANGE=validator)
            self.assertEqual(response.status_code, 206)
            self.assertEqual(self.body(response), self.payload[100:201])
        response = self.response('bytes=100-200', HTTP_IF_RANGE='"outdated"')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.body(response), self.payload)

    def test_missing_file_and_invalid_filename_are_404(self):
        for name in ['missing.mp3', '../sample.mp3', '..\\sample.mp3']:
            with self.assertRaisesMessage(Http404, '音频不存在'):
                audio_response(self.factory.get('/audio/'), name)

    def test_empty_file_and_empty_file_range(self):
        response = audio_response(self.factory.get('/audio/'), 'empty.mp3')
        self.addCleanup(response.close)
        self.assertEqual(self.body(response), b'')
        self.assertEqual(response['Content-Length'], '0')
        response = audio_response(self.factory.get('/audio/', HTTP_RANGE='bytes=0-'), 'empty.mp3')
        self.assertEqual(response.status_code, 416)
        self.assertEqual(response['Content-Range'], 'bytes */0')

    def test_post_is_rejected(self):
        self.assertEqual(self.response(method='post').status_code, 405)

    def test_production_audio_route_uses_range_response(self):
        match = resolve('/media/music/audio/sample.mp3')
        response = match.func(self.factory.get('/audio/', HTTP_RANGE='bytes=50-99'), **match.kwargs)
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 206)
        self.assertEqual(self.body(response), self.payload[50:100])

    async def test_asgi_stream_returns_bounded_exact_range(self):
        request = AsyncRequestFactory().get('/audio/', headers={'Range': 'bytes=200-100000'})
        response = audio_response(request, 'sample.mp3')
        self.addCleanup(response.close)
        self.assertTrue(response.is_async)
        self.assertEqual(response.status_code, 206)
        chunks = [chunk async for chunk in response.streaming_content]
        self.assertTrue(all(len(chunk) <= CHUNK_SIZE for chunk in chunks))
        self.assertEqual(b''.join(chunks), self.payload[200:100001])

    async def test_disconnect_closes_audio_file(self):
        from unittest.mock import patch
        with patch('music.services.audio_stream.open', wraps=open) as opener:
            response = audio_response(AsyncRequestFactory().get('/audio/'), 'sample.mp3')
            # Inspect the generator's file, before and after a partial response.
            file = response._iterator.ag_frame.f_locals['file']
            await anext(response._iterator)
            self.assertFalse(file.closed)
            await response._iterator.aclose()
            self.assertTrue(file.closed)
            response.close()
        opener.assert_called_once()
