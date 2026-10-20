from django.http import JsonResponse
from django.test import Client, SimpleTestCase
from unittest.mock import patch


class NavigatorCsrfTests(SimpleTestCase):
    origin = 'https://l1z00505038.zicp.fun'

    def client_with_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/csrf/', HTTP_HOST='localhost:8084')
        return client

    def test_tunnel_origin_is_accepted_behind_http_proxy(self):
        client = self.client_with_csrf()
        with patch('users.services.navigator_service.insert_navigator_order', return_value=JsonResponse({'code': 200})) as insert:
            response = client.post('/users/insert_navigator_order/', {'id': 1, 'target_index': 0},
                content_type='application/json', HTTP_HOST='localhost:8084', HTTP_ORIGIN=self.origin,
                HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 200)
        insert.assert_called_once()

    def test_untrusted_origin_is_rejected_even_with_valid_token(self):
        client = self.client_with_csrf()
        with patch('users.services.navigator_service.insert_navigator_order') as insert:
            response = client.post('/users/insert_navigator_order/', {}, content_type='application/json',
                HTTP_HOST='localhost:8084', HTTP_ORIGIN='https://untrusted.example',
                HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'csrf_failed')
        insert.assert_not_called()

    def test_missing_csrf_token_still_rejected(self):
        response = Client(enforce_csrf_checks=True).post('/users/insert_navigator_order/', {},
            content_type='application/json', HTTP_ORIGIN=self.origin)
        self.assertEqual(response.status_code, 403)
