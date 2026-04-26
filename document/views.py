from django.shortcuts import render
from document.services import document_service

# Create your views here.
# -------------------------------------  document   ----------------------------------
def publish(request):
    res = document_service.publish(request)
    return res

def get_all(request):
    res = document_service.get_all(request)
    return res

def detail(request, document_id=None):
    res = document_service.detail(request, document_id=document_id)
    return res

def remove(request, document_id):
    res = document_service.remove(request, document_id=document_id)
    return res
