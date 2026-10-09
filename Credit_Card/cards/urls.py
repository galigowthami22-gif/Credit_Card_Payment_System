from django.urls import path
from . import views

urlpatterns = [
    path('', views.card_list, name='card_list'),              # READ
    path('add/', views.add_card, name='add_card'),            # CREATE
    path('edit/<int:card_id>/', views.edit_card, name='edit_card'), # UPDATE
    path('delete/<int:card_id>/', views.delete_card, name='delete_card'), # DELETE
    path('<uuid:payment_reference>/pay/', views.make_payment, name='make_payment'),
]
