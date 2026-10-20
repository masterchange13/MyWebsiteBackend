import io
import json
from pathlib import Path
import tempfile
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from users.models.user_model import User
from .models import Ebook
from .parser import parse_book, archive_path


def epub_bytes():
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        archive.writestr('mimetype', 'application/epub+zip')
        archive.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>')
        archive.writestr('OPS/book.opf', '''<package xmlns:dc="http://purl.org/dc/elements/1.1/">
          <metadata><dc:title>测试图书</dc:title><dc:creator>测试作者</dc:creator></metadata>
          <manifest><item id="two" href="two.xhtml" media-type="application/xhtml+xml"/>
          <item id="one" href="one.xhtml" media-type="application/xhtml+xml"/></manifest>
          <spine><itemref idref="one"/><itemref idref="two"/></spine></package>''')
        archive.writestr('OPS/one.xhtml', '<html><head><style>hidden-css</style></head><body><h1>第一章</h1><p>章节正文</p><script>alert("hidden-script")</script></body></html>')
        archive.writestr('OPS/two.xhtml', '<html><body><h1>第二章</h1><p>第二章正文</p></body></html>')
    return output.getvalue()


class EbookTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        storage = override_settings(MEDIA_ROOT=temporary.name)
        storage.enable()
        self.addCleanup(storage.disable)
        self.directory = Path(temporary.name)
        self.user = User.objects.create(username='reader', password='unused', email='reader@example.test')
        self.other = User.objects.create(username='other', password='unused', email='other@example.test')
        self.login(self.user)

    def login(self, user):
        session = self.client.session
        session['user'] = user.username
        session.save()

    def upload(self, name='book.txt', data=None):
        data = data if data is not None else '第一章 开始\n你好，世界。\n第二章 后续\n第二章的内容。'.encode()
        return self.client.post('/ebooks/', {'file': SimpleUploadedFile(name, data)})

    def book(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        return Ebook.objects.get(pk=response.json()['data']['id'])

    def test_upload_txt_list_and_chapter(self):
        book = self.book()
        listing = self.client.get('/ebooks/').json()['data']
        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0]['title'], 'book')
        self.assertEqual(len(listing[0]['chapters']), 2)
        self.assertNotIn('file', listing[0])
        response = self.client.get(f'/ebooks/{book.pk}/chapters/0/')
        self.assertIn('你好', response.json()['data']['text'])
        self.assertTrue((self.directory / book.file.name).is_file())

    def test_utf16_and_gb18030_txt_are_supported(self):
        for encoding in ['utf-16', 'gb18030']:
            response = self.upload(f'{encoding}.txt', '中文正文'.encode(encoding))
            self.assertEqual(response.status_code, 200)
            book_id = response.json()['data']['id']
            self.assertEqual(self.client.get(f'/ebooks/{book_id}/chapters/0/').json()['data']['text'], '中文正文')

    def test_epub_metadata_spine_order_and_safe_plain_text(self):
        response = self.upload('sample.epub', epub_bytes())
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['title'], '测试图书')
        self.assertEqual(data['author'], '测试作者')
        self.assertEqual(data['chapters'][0]['title'], '第一章')
        chapter = self.client.get(f"/ebooks/{data['id']}/chapters/0/").json()['data']['text']
        self.assertNotIn('hidden-script', chapter)
        self.assertNotIn('hidden-css', chapter)

    def test_user_cannot_read_download_change_or_delete_another_users_book(self):
        book = self.book()
        self.login(self.other)
        self.assertEqual(self.client.get('/ebooks/').json()['data'], [])
        for suffix in ['', 'file/', 'chapters/0/']:
            self.assertEqual(self.client.get(f'/ebooks/{book.pk}/{suffix}').status_code, 404)
        self.assertEqual(self.client.post(f'/ebooks/{book.pk}/progress/', {}, content_type='application/json').status_code, 404)
        self.assertEqual(self.client.delete(f'/ebooks/{book.pk}/').status_code, 404)
        self.assertTrue(Ebook.objects.filter(pk=book.pk).exists())

    def test_no_session_requires_login(self):
        book = self.book()
        self.client.session.flush()
        for path in ['/ebooks/', f'/ebooks/{book.pk}/', f'/ebooks/{book.pk}/file/']:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.upload().status_code, 401)

    def test_progress_saved_and_returned_on_reopen(self):
        book = self.book()
        payload = {'chapter': 1, 'scroll': 0.6, 'page': 1, 'font_size': 22, 'theme': 'dark'}
        response = self.client.post(f'/ebooks/{book.pk}/progress/', payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        detail = self.client.get(f'/ebooks/{book.pk}/').json()['data']
        self.assertEqual(detail['progress'], payload)
        self.assertIsNotNone(detail['last_read_at'])

    def test_invalid_progress_does_not_change_existing_progress(self):
        book = self.book()
        for payload in [{'chapter': 999}, {'scroll': float('nan')}, {'font_size': 1000}, ['invalid']]:
            response = self.client.post(f'/ebooks/{book.pk}/progress/', json.dumps(payload), content_type='application/json')
            self.assertEqual(response.status_code, 400)
        book.refresh_from_db()
        self.assertEqual(book.progress, {})

    def test_download_is_exact_and_delete_removes_both_files(self):
        book = self.book()
        paths = [self.directory / book.file.name, self.directory / book.content.name]
        response = self.client.get(f'/ebooks/{book.pk}/file/')
        self.assertIn(b'\xe4\xbd\xa0\xe5\xa5\xbd', b''.join(response.streaming_content))
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        response.close()
        self.assertEqual(self.client.delete(f'/ebooks/{book.pk}/').status_code, 200)
        self.assertFalse(any(path.exists() for path in paths))

    def test_pdf_file_validation_and_download(self):
        data = b'%PDF-1.7\nfixture'
        response = self.upload('sample.pdf', data)
        self.assertEqual(response.status_code, 200)
        book_id = response.json()['data']['id']
        response = self.client.get(f'/ebooks/{book_id}/file/')
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(b''.join(response.streaming_content), data)
        response.close()
        self.assertEqual(self.upload('fake.pdf', b'invalid').status_code, 400)

    def test_invalid_or_unsupported_books_are_not_saved(self):
        for filename, data in [('file.exe', b'ignored'), ('empty.txt', b''), ('bad.epub', b'invalid'), ('binary.txt', b'a\x00b')]:
            self.assertEqual(self.upload(filename, data).status_code, 400)
        self.assertEqual(Ebook.objects.count(), 0)
        self.assertEqual(list(self.directory.rglob('*')), [])

    @override_settings(EBOOK_MAX_UPLOAD_MB=1)
    def test_upload_size_is_bounded(self):
        self.assertEqual(self.upload(data=b'x' * (1024 * 1024 + 1)).status_code, 413)

    def test_entity_expansion_and_archive_traversal_are_rejected(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('META-INF/container.xml', '<!DOCTYPE container [<!ENTITY x "expanded">]><container>&x;</container>')
        self.assertEqual(self.upload('unsafe.epub', output.getvalue()).status_code, 400)
        for path in ['../../outside.html', 'https://example.org/chapter.xhtml', '%2foutside.html']:
            with self.assertRaises(ValueError):
                archive_path('OPS', path)

    def test_very_long_text_is_split_for_mobile_reading(self):
        _, _, chapters = parse_book(('正文' * 25000).encode(), 'txt')
        self.assertGreater(len(chapters), 1)
        self.assertTrue(all(len(chapter['text']) <= 20000 for chapter in chapters))
