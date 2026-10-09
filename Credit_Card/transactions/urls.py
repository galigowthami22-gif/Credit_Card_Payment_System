from django.urls import path
from .views import (transaction_history, transaction_detail)

urlpatterns = [
    path("", transaction_history, name="transaction-history"),
    path("<int:transaction_id>/", transaction_detail, name="transaction-detail")]