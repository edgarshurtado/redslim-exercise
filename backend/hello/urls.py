from django.urls import path
from . import views

urlpatterns = [
    path('redslim-hello', views.hello),
]
