import json
from datetime import timedelta

from django.http import Http404
from django.test import RequestFactory, TestCase
from django.utils import timezone

from to_do_list.models.to_do_list_model import ToDoList
from to_do_list.services import to_do_list_service as service
from users.models.user_model import User


class TodoEditingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(username='todo-owner', password='test', email='owner@example.com')

    def request(self, path, data):
        request = self.factory.post(path, data=json.dumps(data), content_type='application/json')
        request.session = {'user': self.user.username}
        return request

    def test_new_todo_can_be_edited_without_reloading(self):
        added = service.add_to_do_list(self.request('/todo/add', {'title': '原内容'}))
        todo = json.loads(added.content)['data']
        self.assertIn('id', todo)
        self.assertIn('created_time', todo)
        self.assertIn('updated_time', todo)

        edited = service.done_edit(self.request('/todo/doneEdit', {'id': todo['id'], 'title': ' 修改内容 '}))
        saved = json.loads(edited.content)['data']
        self.assertEqual(saved['id'], todo['id'])
        self.assertEqual(saved['title'], '修改内容')
        self.assertEqual(saved['created_time'], todo['created_time'])
        self.assertEqual(ToDoList.objects.get(pk=todo['id']).title, '修改内容')

    def test_edit_preserves_completion_and_returns_updated_time(self):
        todo = ToDoList.objects.create(user=self.user, title='原内容', completed=True)
        old_time = timezone.now() - timedelta(days=1)
        ToDoList.objects.filter(pk=todo.id).update(updated_time=old_time)
        response = service.done_edit(self.request('/todo/doneEdit', {'id': todo.id, 'title': '新内容'}))
        todo.refresh_from_db()
        self.assertTrue(todo.completed)
        self.assertGreater(todo.updated_time, old_time)
        data = json.loads(response.content)['data']
        self.assertTrue(data['completed'])
        self.assertIn('updated_time', data)

    def test_invalid_edit_does_not_overwrite_existing_title(self):
        todo = ToDoList.objects.create(user=self.user, title='原内容')
        for title in ('', '   ', None, 123):
            with self.subTest(title=title):
                response = service.done_edit(self.request('/todo/doneEdit', {'id': todo.id, 'title': title}))
                self.assertEqual(response.status_code, 400)
                todo.refresh_from_db()
                self.assertEqual(todo.title, '原内容')

    def test_edit_requires_id(self):
        response = service.done_edit(self.request('/todo/doneEdit', {'title': '新内容'}))
        self.assertEqual(response.status_code, 400)

    def test_cannot_edit_another_users_todo(self):
        other_user = User.objects.create(username='other', password='test', email='other@example.com')
        todo = ToDoList.objects.create(user=other_user, title='其他用户内容')
        with self.assertRaises(Http404):
            service.done_edit(self.request('/todo/doneEdit', {'id': todo.id, 'title': '新内容'}))
        todo.refresh_from_db()
        self.assertEqual(todo.title, '其他用户内容')

    def test_invalid_new_title_does_not_create_todo(self):
        response = service.add_to_do_list(self.request('/todo/add', {'title': '   '}))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ToDoList.objects.exists())
