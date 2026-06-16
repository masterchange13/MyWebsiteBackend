from django.shortcuts import render
from file.services import file_service

# Create your views here.
# @require_POST
# @csrf_exempt
def upload(request):
    res = file_service.upload(request)
    return res

def list_files(request):
    res = file_service.list_files(request)
    return res

def open_file(request, filename):
    res = file_service.open_file(request, filename)
    return res

def download_file(request, filename):
    res = file_service.download_file(request, filename)
    return res
