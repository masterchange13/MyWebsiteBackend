from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from users.services import user_service

from users.services import navigator_service
from users.services import admin_owner_service

# Create your views here.


def index(_request):
    return HttpResponse('<h1> welcome to my website')


@csrf_exempt
@require_POST
def login(request):
    res = user_service.login(request)
    return res


def test(request):
    res = user_service.test(request)
    return res


@require_POST
def save_icon(request):
    res = navigator_service.save_icon(request)
    return res


def get_all_navigators(request):
    res = navigator_service.get_all_navigators(request)
    return res


@require_POST
def add_icon(request):
    res = navigator_service.add_icon(request)
    return res


@require_POST
def update_icon(request):
    res = navigator_service.update_icon(request)
    return res


@require_POST
def update_navigator_order(request):
    res = navigator_service.update_navigator_order(request)
    return res


@require_POST
def insert_navigator_order(request):
    res = navigator_service.insert_navigator_order(request)
    return res


@require_POST
def swap_navigator_order(request):
    res = navigator_service.swap_navigator_order(request)
    return res


@require_http_methods(["DELETE"])
def remove_icon(request):
    res = navigator_service.remove_icon(request)
    return res


def get_me(request):
    res = user_service.get_me(request)
    return res


def get_user_detail(request, user_id=None):
    res = user_service.get_user_detail(request, user_id=user_id)
    return res


def assign_admin_owner(request):
    res = admin_owner_service.assign_admin_owner(request)
    return res


@require_POST
def logout(request):
    res = user_service.logout(request)
    return res


@csrf_exempt
@require_POST
def register(request):
    res = user_service.register(request)
    return res


@csrf_exempt
@require_POST
def update_user(request):
    res = user_service.update_user(request)
    return res
