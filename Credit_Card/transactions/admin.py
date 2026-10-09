import csv
from decimal import Decimal

from django.contrib import admin
from django.contrib.admin.models import CHANGE, LogEntry
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils import timezone

from .models import Transaction


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ("action_time", "user", "content_type", "object_repr", "action_flag")
    list_filter = ("action_flag", "content_type", "action_time")
    search_fields = ("object_repr", "change_message", "user__username")
    readonly_fields = (
        "action_time",
        "user",
        "content_type",
        "object_id",
        "object_repr",
        "action_flag",
        "change_message",
    )
    ordering = ("-action_time",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return (
            request.user.is_superuser
            or request.user.has_perm("transactions.change_transaction")
            or self.has_view_permission(request, obj)
        )

    def has_delete_permission(self, request, obj=None):
        return False


def _csv_safe(value):
    value = "" if value is None else str(value)
    if value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    change_list_template = "admin/transactions/transaction/change_list.html"

    list_display = (
        "transaction_id",
        "user_id",
        "card_last_four",
        "amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("status", "currency", "created_at")
    search_fields = ("transaction_id", "card_last_four")
    readonly_fields = (
        "id",
        "user_id",
        "card_id",
        "amount",
        "currency",
        "status",
        "transaction_id",
        "card_last_four",
        "failure_reason",
        "created_at",
        "updated_at",
    )
    actions = ("export_transactions_csv",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_all_transactions_csv),
                name="transactions_transaction_export_csv",
            ),
        ]
        return custom_urls + urls

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return self.has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        today = timezone.localdate()
        summary = Transaction.objects.filter(created_at__date=today).aggregate(
            total_transactions=Count("pk"),
            successful_payments=Count("pk", filter=Q(status="SUCCESS")),
            failed_payments=Count("pk", filter=Q(status="FAILED")),
            pending_payments=Count("pk", filter=Q(status="PENDING")),
            total_payment_amount=Sum("amount", default=Decimal("0.00")),
        )
        context = {
            **(extra_context or {}),
            "daily_summary": summary,
            "summary_date": today,
            "export_csv_url": reverse("admin:transactions_transaction_export_csv"),
        }
        return super().changelist_view(request, extra_context=context)

    def _csv_response(self, request, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="transactions.csv"'
        writer = csv.writer(response)
        writer.writerow(
            (
                "Transaction ID",
                "User ID",
                "Card ID",
                "Card Last 4",
                "Amount",
                "Currency",
                "Status",
                "Failure Reason",
                "Created At",
            )
        )
        for transaction in queryset:
            writer.writerow(
                _csv_safe(value)
                for value in (
                    transaction.transaction_id,
                    transaction.user_id,
                    transaction.card_id,
                    transaction.card_last_four,
                    transaction.amount,
                    transaction.currency,
                    transaction.status,
                    transaction.failure_reason,
                    transaction.created_at,
                )
            )

        LogEntry.objects.log_actions(
            user_id=request.user.pk,
            queryset=queryset,
            action_flag=CHANGE,
            change_message="Exported transaction record to CSV.",
        )
        return response

    def export_all_transactions_csv(self, request):
        if not self.has_view_permission(request):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        queryset = self.get_queryset(request).order_by("-created_at")
        return self._csv_response(request, queryset)

    @admin.action(description="Export selected transactions to CSV", permissions=("view",))
    def export_transactions_csv(self, request, queryset):
        return self._csv_response(request, queryset)
