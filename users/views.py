from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users.services import login_service

from users.services import navigator_service 

# Create your views here.

def index(request):
    return HttpResponse('<h1> welcome to my website')

@require_POST
@csrf_exempt
def login(request):
    res = login_service.login(request)
    return res

def test(request):
    res = login_service.test(request)
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

@require_http_methods(["DELETE"])
def remove_icon(request):
    res = navigator_service.remove_icon(request)
    return res
