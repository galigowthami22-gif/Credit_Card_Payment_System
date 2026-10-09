"""Credit Card Payment System requirements.

Backend and database: Django and FastAPI backed by MySQL.

1. User authentication (Django)
   - Register and log in using JWT authentication; support logout.
   - Hash passwords and protect authenticated routes.
2. Card management (Django)
   - Add, view, and delete saved credit/debit cards.
   - Never store full card numbers or CVVs; keep only masked numbers and last four digits.
3. Payment processing (FastAPI)
   - Simulate payments, beginning in PENDING and ending in SUCCESS or FAILED.
4. Transaction management (Django)
   - Show transaction history with date, amount, and status filters.
   - Allow administrators to export transactions as CSV.
5. Django Admin
   - Manage users and view cards and transactions.
   - Show a daily payment summary.
   - Enforce Admin, Manager, and User roles: Admin has full access; Manager can
     manage users/cards and view/export transactions; Users access only their
     own cards and transactions.
6. Database
   - Maintain users, cards, transactions, and administrator activity logs in MySQL.
7. Security
   - Do not store CVVs; hash passwords; require JWT authentication.
   - Validate inputs and use parameterized ORM/database operations to prevent SQL injection.
8. API documentation
   - Keep FastAPI Swagger enabled and provide Django API documentation and a Postman collection.
9. Testing
   - Include unit tests for authentication, card management, and payment processing.
"""

from django.db import models

class Transaction(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed")]
    
    id = models.BigAutoField(primary_key=True)
    user_id = models.IntegerField(db_index=True)
    card_id = models.IntegerField(db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    card_last_four = models.CharField(max_length=4)
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:

        db_table = "payments"
        managed = False
        ordering = ["-created_at"]

    def __str__(self):
        return self.transaction_id