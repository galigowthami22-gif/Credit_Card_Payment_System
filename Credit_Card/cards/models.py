from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import uuid
import re

class Card(models.Model):
    payment_reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cards')
    card_holder_name = models.CharField(max_length=255)
    masked_card_number = models.CharField(max_length=19) # e.g. **** **** **** 1234
    last_four_digits = models.CharField(max_length=4)
    expiry_date = models.CharField(max_length=5) # e.g. 12/25
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if not re.fullmatch(r"\*{4} \*{4} \*{4} [0-9]{4}", self.masked_card_number or ""):
            raise ValidationError({"masked_card_number": "Store only the masked card number."})
        if self.masked_card_number[-4:] != self.last_four_digits:
            raise ValidationError({"last_four_digits": "Must match the masked card number."})

    def __str__(self):
        return f"{self.card_holder_name} - {self.masked_card_number}"
