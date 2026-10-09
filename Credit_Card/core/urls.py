from django.contrib import admin
from django.urls import path, include
from transactions.views import transaction_history_page
from cards.views import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('users.urls')),
    path('cards/', include('cards.urls')),
    path('transactions/', transaction_history_page, name='transaction-history-page'),
    path('api/', include('transactions.urls')),
    path('', dashboard, name='dashboard'),
]