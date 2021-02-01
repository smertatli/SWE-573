from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.check_user, name='check_user'),
    path('login', views._login, name='login'),
    path('signup', views._signup, name='signup'),
    path('main', views._login, name='main'),
    path('looknfeel', views._looknfeel, name='looknfeel'),
    path('ajax/looknfeel', views._sniff_tweets, name='snifftweets'),
    path('logout/', views.logout, name='logout'),
    

]
