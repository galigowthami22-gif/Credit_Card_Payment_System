from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('token/', views.token_view, name='api-token'),
    path('logout/', views.logout_view, name='logout'),
]
