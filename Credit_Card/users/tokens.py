from functools import wraps
from datetime import UTC, datetime, timedelta
from typing import Callable, TypeVar

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from cards.models import Card

View = TypeVar("View", bound=Callable)


def create_access_token(user_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_payment_authorization_token(user_id: int, card: Card) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "user_id": user_id,
            "iat": now,
            "exp": now + timedelta(minutes=2),
            "scope": "payment",
            "payment_reference": str(card.payment_reference),
            "card_last_four": card.last_four_digits,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def jwt_required(view: View) -> View:
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        authorization = request.headers.get("Authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not separator or not token:
            return JsonResponse({"detail": "Bearer token required."}, status=401)

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"require": ["exp", "iat", "user_id"]},
            )
        except jwt.InvalidTokenError:
            return JsonResponse({"detail": "Invalid or expired token."}, status=401)

        user_id = payload.get("user_id")
        if isinstance(user_id, bool) or not isinstance(user_id, int):
            return JsonResponse({"detail": "Invalid or expired token."}, status=401)

        user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            return JsonResponse({"detail": "Invalid or expired token."}, status=401)

        request.user = user
        return view(request, *args, **kwargs)

    return wrapped
