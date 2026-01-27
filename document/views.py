from django.shortcuts import render
from document.services import document_service

# Create your views here.
def publish(request):
    res = document_service.publish(request)
    return res

def get_all(request):
    res = document_service.get_all(request)
    return res