from django.shortcuts import render

# Create your views here.
from agent.services import agent_service

def list_conversations(request):
    return agent_service.list_conversations(request)

def create_conversation(request):
    return agent_service.create_conversation(request)

def list_messages(request):
    return agent_service.list_messages(request)

def chat_stream(request):
    return agent_service.chat_stream(request)
