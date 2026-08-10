from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt

from decisionHelper import services


@csrf_exempt
@require_POST
def record_decision(request):
    return services.record_decision(request)


def get_history(request):
    return services.get_history(request)


@csrf_exempt
@require_http_methods(["DELETE"])
def clear_history(request):
    return services.clear_history(request)
