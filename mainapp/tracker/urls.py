from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
     
    path('create/', views.create_track, name='create_track'),
    path('', views.create_track_ajax, name='create_track_ajax')


]