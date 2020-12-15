from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views._login, name='login'),
    path('signup', views._signup, name='signup'),
    path('main', views._login, name='main'),
    path('looknfeel', views._looknfeel, name='looknfeel'),
    path('ajax/looknfeel', views._sniff_tweets, name='snifftweets'),
    path('board/', views.myFirstChart, name='boardchart'),
    

]
