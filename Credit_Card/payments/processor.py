from typing import Literal

SIMULATED_DECLINE_LAST_FOUR = "0002"

def simulate_payment(card_last_four: str) -> tuple[Literal["SUCCESS", "FAILED"], str | None]:
    if card_last_four == SIMULATED_DECLINE_LAST_FOUR:
        return "FAILED", "Payment declined by the simulator."
    return "SUCCESS", None
