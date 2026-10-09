import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from payments.database import (
    create_pending_payment,
    finalize_payment,
    get_payment,
    initialize_database,
)
from payments.processor import simulate_payment
from payments.schemas import PaymentRequest, PaymentResponse

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR.parent / ".env"
if not ENV_FILE.is_file():
    ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "payments.sqlite3"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "default-key"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
bearer_scheme = HTTPBearer(auto_error=False)


def _payment_claims(
    credentials: HTTPAuthorizationCredentials | None,
    payment_reference: str,
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token required.")
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "user_id"]},
        )
    except jwt.InvalidTokenError as error:
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from error

    user_id = payload.get("user_id")
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    if (
        payload.get("scope") != "payment"
        or payload.get("payment_reference") != payment_reference
        or not isinstance(payload.get("card_last_four"), str)
        or len(payload["card_last_four"]) != 4
        or not payload["card_last_four"].isdigit()
    ):
        raise HTTPException(status_code=401, detail="Invalid payment authorization.")
    return payload


def _database_path() -> Path:
    configured_path = os.getenv("PAYMENTS_DATABASE_PATH")
    return Path(configured_path).expanduser() if configured_path else DEFAULT_DATABASE_PATH


def create_app(database_path: Path | None = None) -> FastAPI:
    resolved_database_path = database_path or _database_path()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        initialize_database(resolved_database_path)
        yield

    app = FastAPI(
        title="Credit Card Payment API",
        description=(
            "A local payment-processing simulation. Use fabricated card data only; "
            "this API does not contact a payment provider."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def sanitized_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        del request
        errors = [
            {
                "loc": error["loc"],
                "msg": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.post(
        "/payments",
        response_model=PaymentResponse,
        status_code=201,
        summary="Make a simulated payment",
    )
    def make_payment(
        payment: PaymentRequest,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> PaymentResponse:
        claims = _payment_claims(credentials, str(payment.payment_reference))
        payment_id = create_pending_payment(
            resolved_database_path,
            payment.amount,
            claims["card_last_four"],
        )
        status, failure_reason = simulate_payment(claims["card_last_four"])
        finalize_payment(
            resolved_database_path,
            payment_id,
            status,
            failure_reason,
        )

        record = get_payment(resolved_database_path, payment_id)
        if record is None:
            raise HTTPException(status_code=500, detail="Created payment could not be retrieved.")
        response_record = dict(record)
        response_record["transaction_id"] = f"TXN-{payment_id}"
        return PaymentResponse.model_validate(response_record)

    return app


app = create_app()
