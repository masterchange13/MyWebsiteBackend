"""Extract readable text without executing EPUB HTML or unpacking ZIP paths."""
import io
import posixpath
import re
import zipfile
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from defusedxml import ElementTree

MAX_TEXT = 20 * 1024 * 1024
CHAPTER_SIZE = 20000


def decode_text(data):
    encodings = ['utf-16'] if data.startswith((b'\xff\xfe', b'\xfe\xff')) else ['utf-8-sig', 'gb18030']
    for encoding in encodings:
        try:
            text = data.decode(encoding)
            if '\x00' in text:
                raise ValueError('文件包含二进制数据，不能作为文本阅读。')
            return text.replace('\r\n', '\n').replace('\r', '\n')
        except UnicodeError:
            continue
    raise ValueError('无法识别文本编码，请使用 UTF-8、UTF-16 或 GB18030 文本。')


def split_chapters(chapters):
    output = []
    total = 0
    for title, text in chapters:
        text = text.strip()
        if not text:
            continue
        total += len(text.encode('utf-8'))
        if total > MAX_TEXT:
            raise ValueError('电子书正文过大，最多支持 20 MB 的提取文本。')
        for start in range(0, len(text), CHAPTER_SIZE):
            part = start // CHAPTER_SIZE + 1
            output.append({'title': (title or '正文')[:150] + (f' · {part}' if start else ''), 'text': text[start:start + CHAPTER_SIZE]})
    if not output:
        raise ValueError('没有找到可阅读的正文。')
    return output


class ChapterText(HTMLParser):
    blocks = {'p', 'div', 'section', 'article', 'h1', 'h2', 'h3', 'h4', 'li', 'br', 'tr', 'blockquote'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'head', 'svg'):
            self.hidden += 1
        if not self.hidden and tag in self.blocks:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'head', 'svg'):
            self.hidden = max(0, self.hidden - 1)
        if not self.hidden and tag in self.blocks:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

    def text(self):
        return re.sub(r'\n[ \t]*\n+', '\n\n', ''.join(self.parts)).strip()


def archive_path(base, href):
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or '\\' in href:
        raise ValueError('EPUB 引用了无效的外部资源。')
    path = posixpath.normpath(posixpath.join(base, unquote(parsed.path)))
    if path.startswith(('../', '/')) or path == '..':
        raise ValueError('EPUB 资源路径无效。')
    return path


def local_name(tag):
    return tag.rsplit('}', 1)[-1]


def parse_epub(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 3000 or sum(item.file_size for item in entries) > 100 * 1024 * 1024:
                raise ValueError('EPUB 解压后体积或文件数量过大。')
            if any(item.flag_bits & 1 for item in entries):
                raise ValueError('暂不支持加密 EPUB。')
            container = ElementTree.fromstring(archive.read('META-INF/container.xml'))
            rootfile = next(node for node in container.iter() if local_name(node.tag) == 'rootfile')
            package_path = archive_path('', rootfile.attrib['full-path'])
            package = ElementTree.fromstring(archive.read(package_path))
            metadata = next((node for node in package if local_name(node.tag) == 'metadata'), [])
            title = next((''.join(node.itertext()).strip() for node in metadata if local_name(node.tag) == 'title'), '')
            author = next((''.join(node.itertext()).strip() for node in metadata if local_name(node.tag) == 'creator'), '')
            manifest = {node.attrib['id']: node.attrib for node in package.iter() if local_name(node.tag) == 'item' and 'id' in node.attrib}
            chapters = []
            total = 0
            for node in package.iter():
                if local_name(node.tag) != 'itemref':
                    continue
                item = manifest.get(node.attrib.get('idref'), {})
                if item.get('media-type') not in ('application/xhtml+xml', 'text/html'):
                    continue
                path = archive_path(posixpath.dirname(package_path), item['href'])
                raw = archive.read(path)
                total += len(raw)
                if total > MAX_TEXT:
                    raise ValueError('EPUB 正文过大。')
                parser = ChapterText()
                parser.feed(raw.decode('utf-8-sig'))
                text = parser.text()
                if text:
                    heading = next((line.strip() for line in text.splitlines() if line.strip()), f'第 {len(chapters) + 1} 章')
                    chapters.append((heading[:100], text))
            return title, author, split_chapters(chapters)
    except (zipfile.BadZipFile, KeyError, StopIteration, UnicodeError, ElementTree.ParseError) as error:
        raise ValueError('EPUB 格式无效，或正文已加密，无法读取。') from error


def parse_book(data, extension):
    if extension == 'pdf':
        if not data[:1024].lstrip().startswith(b'%PDF-'):
            raise ValueError('文件不是有效的 PDF。')
        return '', '', []
    if extension == 'epub':
        return parse_epub(data)
    text = decode_text(data)
    chapters, lines, heading = [], [], '正文'
    for line in text.splitlines():
        if (re.match(r'^\s*(第.{1,30}[章回节卷部篇]|chapter\s+\d+)', line, re.IGNORECASE)
                and len(line.strip()) < 120 and not re.search(r'[。！？!?；;]$', line.strip())):
            if lines:
                chapters.append((heading, '\n'.join(lines)))
            heading, lines = line.strip(), [line]
        else:
            lines.append(line)
    if lines:
        chapters.append((heading, '\n'.join(lines)))
    return '', '', split_chapters(chapters)
