from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("new/", views.new_chat, name="new_chat"),
    path("delete/<int:chat_id>/", views.delete_chat, name="delete_chat"),
]