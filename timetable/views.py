from django.shortcuts import render
from timetable.services import timetable_service

# Create your views here.
# ---------------------------------        timetable          ----------------------------------
def get_list(request):
    res = timetable_service.get_list(request)
    return res

def add_entry(request):
    res = timetable_service.add_entry(request)
    return res

def update_entry(request):
    res = timetable_service.update_entry(request)
    return res

def remove_entry(request):
    res = timetable_service.remove_entry(request)
    return res

def get_config(request):
    res = timetable_service.get_config(request)
    return res

def save_config(request):
    res = timetable_service.save_config(request)
    return res
