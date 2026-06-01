from django.urls import path
from agent import views as agent_views

urlpatten = [
    path('conversations/', agent_views.list_conversations),
    path('conversations/create/', agent_views.create_conversation),
    path('messages/', agent_views.list_messages),
    path('chat_stream/', agent_views.chat_stream),
]
