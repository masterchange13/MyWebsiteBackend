from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt

from emailer import services


def get_smtp_config(request):
    return services.get_smtp_config(request)


@csrf_exempt
@require_POST
def save_smtp_config(request):
    return services.save_smtp_config(request)


@csrf_exempt
@require_POST
def send_email(request):
    return services.send_email(request)


def get_history(request):
    return services.get_history(request)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_history(request):
    return services.delete_history(request)
