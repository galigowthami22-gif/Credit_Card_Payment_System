from datetime import date
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from users.tokens import jwt_required
from .models import Transaction


def _filtered_transactions(request):
    transactions = Transaction.objects.filter(user_id=request.user.id)

    date_value = request.GET.get("date")
    if date_value:
        try:
            date.fromisoformat(date_value)
        except ValueError as error:
            raise ValueError("Date must use YYYY-MM-DD format.") from error
        transactions = transactions.filter(created_at__date=date_value)

    amount_value = request.GET.get("amount")
    if amount_value:
        try:
            amount = Decimal(amount_value)
        except InvalidOperation as error:
            raise ValueError("Amount must be a valid number.") from error
        if not amount.is_finite():
            raise ValueError("Amount must be a finite number.")
        transactions = transactions.filter(amount=amount)

    status_value = request.GET.get("status")
    if status_value:
        status = status_value.upper()
        valid_statuses = {value for value, _ in Transaction.STATUS_CHOICES}
        if status not in valid_statuses:
            raise ValueError("Status is not valid.")
        transactions = transactions.filter(status=status)

    return transactions


@jwt_required
def transaction_history(request):
    try:
        transactions = _filtered_transactions(request)
    except ValueError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    data = []
    for transaction in transactions:
        data.append({
            "transaction_id": transaction.id,
            "amount": str(transaction.amount),
            "status": transaction.status,
            "card_id": transaction.card_id,
            "created_at": transaction.created_at,
            "failure_reason": transaction.failure_reason})
    return JsonResponse({"transactions": data})


@login_required
def transaction_history_page(request):
    try:
        transactions = _filtered_transactions(request)
    except ValueError as error:
        messages.error(request, str(error))
        transactions = Transaction.objects.none()
    return render(
        request,
        "transactions/history.html",
        {"transactions": transactions},
    )


@jwt_required
def transaction_detail(request, transaction_id):

    transaction = get_object_or_404(
        Transaction,
        id=transaction_id,
        user_id=request.user.id,
    )
    return JsonResponse({
        "transaction_id": transaction.id,
        "amount": str(transaction.amount),
        "status": transaction.status,
        "card_id": transaction.card_id,
        "created_at": transaction.created_at,
        "failure_reason": transaction.failure_reason})