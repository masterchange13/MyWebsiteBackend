import asyncio
import json
import queue
from io import StringIO
from unittest.mock import patch

from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.sessions import SessionMiddlewareStack
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.management import call_command, CommandError
from django.test import Client, TestCase, TransactionTestCase, override_settings

from users.models.user_model import User
from .routing import websocket_urlpatterns


class TerminalApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create(username='terminal-owner', password='unused', email='owner@example.test', can_use_terminal=True)

    def login(self, user):
        session = self.client.session
        session['user'] = user.username
        session.save()

    def test_unauthenticated_cannot_create_terminal(self):
        self.assertEqual(self.client.get('/terminal/status/').status_code, 401)
        self.assertEqual(self.client.post('/terminal/session/').status_code, 401)
        self.assertEqual(self.client.post('/terminal/session/close/').status_code, 401)

    def test_ordinary_account_cannot_create_terminal(self):
        other = User.objects.create(username='reader', password='unused', email='reader@example.test')
        self.login(other)
        self.assertEqual(self.client.post('/terminal/session/').status_code, 403)
        self.assertEqual(self.client.post('/terminal/session/close/').status_code, 403)

    def test_close_targets_only_current_accounts_existing_connection(self):
        self.login(self.user)
        cache.set(f'terminal-session:{self.user.pk}', 'owner-connection')
        cache.set('terminal-session:other', 'other-connection')
        self.assertTrue(self.client.get('/terminal/status/').json()['data']['active_connection'])
        response = self.client.post('/terminal/session/close/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['data']['closing'])
        self.assertTrue(cache.get('terminal-stop:owner-connection'))
        self.assertIsNone(cache.get('terminal-stop:other-connection'))
        # Closing must await process cleanup, rather than deleting an active lease.
        self.assertEqual(cache.get(f'terminal-session:{self.user.pk}'), 'owner-connection')

    def test_close_without_connection_is_idempotent(self):
        self.login(self.user)
        for _ in range(2):
            self.assertFalse(self.client.post('/terminal/session/close/').json()['data']['closing'])

    def test_owner_can_get_configuration_and_short_lived_token(self):
        self.login(self.user)
        status = self.client.get('/terminal/status/')
        self.assertEqual(status.status_code, 200)
        self.assertIn('platform', status.json()['data'])
        response = self.client.post('/terminal/session/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['expires_in'], 60)
        self.assertEqual(response['Cache-Control'], 'no-store')

    @override_settings(TERMINAL_ENABLED=False)
    def test_terminal_can_be_disabled(self):
        self.login(self.user)
        self.assertEqual(self.client.post('/terminal/session/').status_code, 403)

    def test_database_permission_change_takes_effect_without_restart(self):
        self.login(self.user)
        User.objects.filter(pk=self.user.pk).update(can_use_terminal=False)
        self.assertEqual(self.client.post('/terminal/session/').status_code, 403)
        User.objects.filter(pk=self.user.pk).update(can_use_terminal=True)
        self.assertEqual(self.client.post('/terminal/session/').status_code, 200)

    @override_settings(TERMINAL_ALLOWED_USERS=['reader'])
    def test_old_environment_allowlist_cannot_grant_database_permission(self):
        other = User.objects.create(username='reader', password='unused', email='reader@example.test')
        self.login(other)
        self.assertEqual(self.client.post('/terminal/session/').status_code, 403)

    def test_management_command_grants_and_revokes_existing_account(self):
        call_command('set_terminal_permission', self.user.username, '--revoke', stdout=StringIO())
        self.user.refresh_from_db()
        self.assertFalse(self.user.can_use_terminal)
        call_command('set_terminal_permission', self.user.username, stdout=StringIO())
        self.user.refresh_from_db()
        self.assertTrue(self.user.can_use_terminal)
        with self.assertRaises(CommandError):
            call_command('set_terminal_permission', 'missing-account', stdout=StringIO())
        self.assertFalse(User.objects.filter(username='missing-account').exists())

    def test_registration_and_profile_update_cannot_grant_terminal_permission(self):
        response = self.client.post('/users/register/', json.dumps({
            'username': 'new-reader', 'password': 'test-only-password',
            'email': 'new-reader@example.test', 'can_use_terminal': True,
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        other = User.objects.get(username='new-reader')
        self.assertFalse(other.can_use_terminal)
        self.login(other)
        response = self.client.post('/users/update/', json.dumps({'can_use_terminal': True}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        other.refresh_from_db()
        self.assertFalse(other.can_use_terminal)

    def test_token_issuance_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        session = client.session
        session['user'] = self.user.username
        session.save()
        self.assertEqual(client.post('/terminal/session/').status_code, 403)
        self.assertEqual(client.post('/terminal/session/close/').status_code, 403)


class FakeConsole:
    def __init__(self):
        self.output = queue.Queue()
        self.writes = []
        self.sizes = []
        self.closed = False

    def read(self):
        if self.closed:
            raise EOFError()
        try:
            return self.output.get(timeout=0.02)
        except queue.Empty:
            return ''

    def write(self, data):
        self.writes.append(data)

    def resize(self, rows, cols):
        self.sizes.append((rows, cols))

    def close(self):
        self.closed = True


class TerminalSocketTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        User.objects.create(username='terminal-owner', password='unused', email='socket@example.test', can_use_terminal=True)
        session = self.client.session
        session['user'] = 'terminal-owner'
        session.save()
        self.session_key = session.session_key
        self.cookie = f'{settings.SESSION_COOKIE_NAME}={self.session_key}'.encode()
        self.token = self.client.post('/terminal/session/').json()['data']['token']

    def communicator(self, token=None, origin='https://l1z00505038.zicp.fun', cookie=None):
        return WebsocketCommunicator(
            SessionMiddlewareStack(URLRouter(websocket_urlpatterns)),
            '/terminal/ws/?token=' + (token if token is not None else self.token),
            headers=[(b'origin', origin.encode()), (b'host', b'localhost:8084'), (b'cookie', cookie if cookie is not None else self.cookie)],
        )

    async def test_connected_owner_can_input_resize_and_receive_output(self):
        console = FakeConsole()
        with patch('terminal.consumers.Console', return_value=console):
            connection = self.communicator()
            self.assertTrue((await connection.connect())[0])
            self.assertEqual((await connection.receive_json_from())['type'], 'ready')
            console.output.put('terminal-output')
            self.assertEqual((await connection.receive_json_from())['data'], 'terminal-output')
            await connection.send_json_to({'type': 'input', 'data': 'pwd\r'})
            await connection.send_json_to({'type': 'resize', 'rows': 1000, 'cols': 2})
            await connection.send_json_to({'type': 'ping'})
            self.assertEqual((await connection.receive_json_from())['type'], 'pong')
            self.assertEqual(console.writes, ['pwd\r'])
            self.assertEqual(console.sizes, [(120, 20)])
            await connection.disconnect()
        self.assertTrue(console.closed)

    async def test_missing_invalid_and_cross_origin_tokens_are_rejected(self):
        for token, origin, cookie in [('', 'https://l1z00505038.zicp.fun', self.cookie),
                                      ('invalid', 'https://l1z00505038.zicp.fun', self.cookie),
                                      (self.token, 'https://untrusted.example', self.cookie),
                                      (self.token, 'https://l1z00505038.zicp.fun', b'')]:
            connection = self.communicator(token, origin, cookie)
            self.assertFalse((await connection.connect())[0])
            await connection.disconnect()

    async def test_token_cannot_be_replayed(self):
        with patch('terminal.consumers.Console', return_value=FakeConsole()):
            first = self.communicator()
            self.assertTrue((await first.connect())[0])
            await first.receive_json_from()
            second = self.communicator()
            self.assertFalse((await second.connect())[0])
            await second.disconnect()
            await first.disconnect()

    async def test_another_page_can_close_original_connection_and_reconnect(self):
        original, replacement = FakeConsole(), FakeConsole()
        with patch('terminal.consumers.Console', side_effect=[original, replacement]):
            first = self.communicator()
            self.assertTrue((await first.connect())[0])
            await first.receive_json_from()
            token = (await sync_to_async(self.client.post)('/terminal/session/')).json()['data']['token']
            blocked = self.communicator(token)
            self.assertTrue((await blocked.connect())[0])
            self.assertEqual((await blocked.receive_json_from())['reason'], 'connection_exists')
            self.assertEqual((await blocked.receive_output())['code'], 4429)
            await blocked.disconnect()

            response = await sync_to_async(self.client.post)('/terminal/session/close/')
            self.assertEqual(response.status_code, 200)
            message = await first.receive_json_from(timeout=3)
            self.assertIn('已关闭', message['message'])
            self.assertEqual((await first.receive_output(timeout=3))['type'], 'websocket.close')
            await first.disconnect()
            self.assertTrue(original.closed)
            status = await sync_to_async(self.client.get)('/terminal/status/')
            self.assertFalse(status.json()['data']['active_connection'])

            token = (await sync_to_async(self.client.post)('/terminal/session/')).json()['data']['token']
            second = self.communicator(token)
            self.assertTrue((await second.connect())[0])
            self.assertEqual((await second.receive_json_from())['type'], 'ready')
            await second.disconnect()
            self.assertTrue(replacement.closed)

    async def test_revoked_connection_cannot_run_more_commands(self):
        console = FakeConsole()
        with patch('terminal.consumers.Console', return_value=console):
            connection = self.communicator()
            self.assertTrue((await connection.connect())[0])
            await connection.receive_json_from()
            await sync_to_async(self.client.post)('/terminal/session/close/')
            await connection.send_json_to({'type': 'input', 'data': 'must-not-run\r'})
            while (await connection.receive_output(timeout=3))['type'] != 'websocket.close':
                pass
            await connection.disconnect()
        self.assertEqual(console.writes, [])
        self.assertTrue(console.closed)

    async def test_logout_revokes_existing_terminal_on_heartbeat(self):
        with patch('terminal.consumers.Console', return_value=FakeConsole()):
            connection = self.communicator()
            self.assertTrue((await connection.connect())[0])
            await connection.receive_json_from()
            await sync_to_async(lambda: Session.objects.filter(session_key=self.session_key).delete())()
            await connection.send_json_to({'type': 'ping'})
            result = await connection.receive_output()
            self.assertEqual(result['type'], 'websocket.close')
            self.assertEqual(result['code'], 4403)
            await connection.disconnect()

    async def test_database_permission_revocation_closes_existing_socket(self):
        with patch('terminal.consumers.Console', return_value=FakeConsole()) as factory:
            connection = self.communicator()
            self.assertTrue((await connection.connect())[0])
            await connection.receive_json_from()
            await sync_to_async(lambda: User.objects.filter(username='terminal-owner').update(can_use_terminal=False))()
            await connection.send_json_to({'type': 'ping'})
            result = await connection.receive_output()
            self.assertEqual(result['type'], 'websocket.close')
            self.assertEqual(result['code'], 4403)
            await connection.disconnect()
            self.assertTrue(factory.return_value.closed)
