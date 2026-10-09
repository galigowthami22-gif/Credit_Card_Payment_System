from django.contrib import admin

from .models import Card


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("card_holder_name", "user", "masked_card_number", "expiry_date")
    list_filter = ("created_at",)
    search_fields = ("card_holder_name", "last_four_digits", "user__username")
