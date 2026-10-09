from fastapi import FastAPI
from payment_management.payment_router import router as payment_router
from contextlib import asynccontextmanager
from core.database import engine
from payment_management.payment_model import Payment

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Payment.__table__.create(sync_conn, checkfirst=True)
        )
    yield
    await engine.dispose()

app = FastAPI(
    title="Credit Card Payment System",
    description="Payment Processing API",
    version="1.0.0",
    lifespan=lifespan)

app.include_router(payment_router)