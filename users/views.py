from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import csrf_protect

from users.services import login_service

from users.services import navigator_service 

# Create your views here.

def index(request):
    return HttpResponse('<h1> welcome to my website')

@require_POST
@csrf_protect
def login(request):
    res = login_service.login(request)
    return res

def test(request):
    res = login_service.test(request)
    return res

@csrf_protect
@require_POST
def save_icon(request):
    res = navigator_service.save_icon(request)
    return res

def get_all_navigators(request):
    res = navigator_service.get_all_navigators(request)
    return res
