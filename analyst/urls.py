from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_view, name='upload'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('insights/', views.insights_view, name='insights'),
    path('ask/', views.ask_view, name='ask'),
]
