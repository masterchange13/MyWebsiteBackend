from django.shortcuts import render
from to_do_list.services import to_do_list_service

# Create your views here.
# ---------------------------------        to do list          ----------------------------------
def get_to_do_list(request):
    res = to_do_list_service.get_to_do_list(request)
    return res

def add_to_do_list(request):
    res = to_do_list_service.add_to_do_list(request)
    return res

def update_to_do_list(request):
    res = to_do_list_service.update_to_do_list(request)
    return res

def remove_to_do_list(request):
    res = to_do_list_service.remove_to_do_list(request)
    return res


def get_all_to_do_list(request):
    res = to_do_list_service.get_all_to_do_list(request)
    return res

def update_to_do_status(request):
    res = to_do_list_service.update_to_do_status(request)
    return res

def done_edit(request):
    res = to_do_list_service.done_edit(request)
    return res

def remove_completed(request):
    res = to_do_list_service.remove_completed(request)
    return res