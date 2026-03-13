from django.shortcuts import render
from file.services import file_service

# Create your views here.
# @require_POST
# @csrf_exempt
def upload(request):
    res = file_service.upload(request)
    return res