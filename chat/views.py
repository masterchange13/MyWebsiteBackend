from chat.services import chat_service

def get_users(request):
    return chat_service.get_users(request)

def get_history(request):
    return chat_service.get_history(request)
