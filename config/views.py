from django.shortcuts import render

# Create your views here.
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"message": "CSRF cookie set"})
