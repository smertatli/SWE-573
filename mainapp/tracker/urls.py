from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
     
    path('create/', views.create_track, name='create_track'),
    path('', views.create_track_ajax, name='create_track_ajax'),
    path('get_tracks/', views.get_tracks, name='get_tracks'),
    path('cancel_track/', views.cancel_track, name='cancel_track'),
    path('visualize_accumulations/', views.visualize_accumulations, name='visualize_accumulations'),

    
    



]