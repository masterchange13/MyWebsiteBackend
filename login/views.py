from django.shortcuts import render
from django.http import HttpResponse

from login.models.login import login

# Create your views here.

def login(request):
    login(request)
    return HttpResponse('<h1> welcome to login')
