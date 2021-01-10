from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
     
    path('dashboard/', views.show_dashboard, name='show_dashboard'),
    path('', views.get_basic_counts, name='get_basic_counts'),
    path('entity_domain/', views.get_domain_entity, name='get_domain_entity'),
    path('domains/', views.get_domain_table, name='get_domain_table'),
    path('entities/', views.get_entity_table, name='get_entity_table'),

    


]