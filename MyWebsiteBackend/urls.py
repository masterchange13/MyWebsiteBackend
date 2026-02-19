"""
URL configuration for MyWebsiteBackend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from users import urls as users_urls
from users import views as login_views
from config import views as config_views
from document import urls as document_urls
from to_do_list import urls as to_do_list_urls
from music import urls as music_urls
from agent import urls as agent_urls
from chat import urls as chat_urls

urlpatterns = [
    # urls.py
    path("csrf/", config_views.csrf),
    path('test/', login_views.index, name='index'),
    path('admin/', admin.site.urls),
    path('users/', include(users_urls.urlpatten)),
    path('document/', include(document_urls.urlpatten)),
    path('todo/', include(to_do_list_urls.urlpatten)),
    # music/
    path('music/', include(music_urls.urlpatten)),
    path('media/music/', include(music_urls.media_url)),
    # agent/
    path('agent/', include(agent_urls.urlpatten)),
    # chat
    path('chat/', include(chat_urls.urlpatten)),
]
