from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
     
    path('dashboard/', views.show_dashboard, name='show_dashboard'),
    path('', views.get_basic_counts, name='get_basic_counts'),
    path('entity_domain/', views.get_domain_entity, name='get_domain_entity'),
    path('domains/', views.get_domain_table, name='get_domain_table'),
    path('entities/', views.get_entity_table, name='get_entity_table'),
    path('users/', views.get_user_table, name='get_user_table'),
    path('tracks/', views.get_tracks, name='get_tracks'),
    path('domain_entity_analysis/', views.domain_entity_analysis, name='domain_entity_analysis'),
    path('domain_entity_analysis_ajax/', views.get_domain_for_graph, name='get_domain_for_graph'),
    path('domain_entity_analysis_ajax2/', views.get_entity_for_graph, name='get_entity_for_graph'),
    path('call_ajax/', views.call_ajax, name='call_ajax'),
    path('tweet_preprocessor/', views.tweet_preprocessor, name='tweet_processor'),
    path('network_analyzer/', views.network_analyzer, name='network_analyzer'),
    path('tweet_media_analyzer/', views.tweet_media_analyzer, name='tweet_media_analyzer'),
    path('comparisor/', views.comparisor, name='comparisor'),
    

    


]