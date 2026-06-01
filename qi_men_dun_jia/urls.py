from django.urls import path
from qi_men_dun_jia import views

urlpatten = [
    path('calc', views.calc),
    path('analyze', views.analyze),
    path('history', views.history),
    path('result/<int:calc_id>', views.result),
]
