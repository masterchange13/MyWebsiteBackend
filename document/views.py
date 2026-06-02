from django.shortcuts import render
from document.services import document_service
from document.services import comment_service

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

# -------------------------------------  comment   ----------------------------------
def add_comment(request):
    return comment_service.add_comment(request)

def get_comments(request):
    return comment_service.get_comments(request)

def delete_comment(request, comment_id):
    return comment_service.delete_comment(request, comment_id)
