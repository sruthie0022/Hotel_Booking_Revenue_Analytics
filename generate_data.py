"""Generate reproducible synthetic booking and daily inventory CSV files."""

import csv
import random
from datetime import date, timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BOOKING_COUNT = 6_500
SEED = 42

ROOM_TYPES = ["Standard Double", "Superior", "Deluxe", "Family", "Suite"]
ROOM_WEIGHTS = [0.36, 0.23, 0.19, 0.14, 0.08]
CHANNELS = ["Online Travel Agent", "Direct Website", "Corporate", "Offline Travel Agent", "Phone"]
CHANNEL_WEIGHTS = [0.40, 0.27, 0.13, 0.12, 0.08]
CUSTOMER_TYPES = ["Transient", "Contract", "Transient-Party", "Group"]
CUSTOMER_WEIGHTS = [0.63, 0.12, 0.18, 0.07]
COUNTRIES = ["Portugal", "United Kingdom", "France", "Spain", "Germany", "Ireland", "Italy", "United States", "Belgium", "Other"]
COUNTRY_WEIGHTS = [0.27, 0.15, 0.12, 0.10, 0.08, 0.07, 0.06, 0.05, 0.04, 0.06]
BASE_RATES = {
    "Standard Double": 105,
    "Superior": 142,
    "Deluxe": 188,
    "Family": 205,
    "Suite": 282,
}
MONTH_WEIGHTS = [0.055, 0.055, 0.065, 0.075, 0.085, 0.095, 0.115, 0.115, 0.095, 0.085, 0.08, 0.08]
MONTH_RATE = [0.78, 0.80, 0.88, 0.96, 1.03, 1.12, 1.24, 1.22, 1.08, 0.99, 0.88, 0.94]
NIGHT_LENGTHS = [1, 2, 3, 4, 5, 6, 7, 8, 9]
NIGHT_WEIGHTS = [0.17, 0.28, 0.24, 0.13, 0.08, 0.045, 0.03, 0.015, 0.005]
BOOKING_COLUMNS = [
    "booking_id", "booking_date", "arrival_date", "room_type", "booking_channel",
    "market_segment", "customer_type", "country", "meal", "lead_time",
    "stays_in_weekend_nights", "stays_in_week_nights", "total_nights", "adults",
    "children", "babies", "total_guests", "rooms_booked", "adr", "is_canceled",
    "reservation_status", "revenue",
]
INVENTORY_COLUMNS = ["date", "room_type", "total_rooms"]


def _arrival_date(rng: random.Random) -> date:
    year = rng.choice([2023, 2024, 2025])
    month = rng.choices(range(1, 13), weights=MONTH_WEIGHTS, k=1)[0]
    first_day = date(year, month, 1)
    next_month = date(year + (month == 12), month % 12 + 1, 1)
    return first_day + timedelta(days=rng.randrange((next_month - first_day).days))


def _booking_rows(rng: random.Random) -> list[dict[str, object]]:
    rows = []
    for index in range(1, BOOKING_COUNT + 1):
        arrival = _arrival_date(rng)
        nights = rng.choices(NIGHT_LENGTHS, weights=NIGHT_WEIGHTS, k=1)[0]
        departure = arrival + timedelta(days=nights)
        lead_time = max(0, int(rng.triangular(0, 240, 42)))
        booking_date = arrival - timedelta(days=lead_time)
        room_type = rng.choices(ROOM_TYPES, weights=ROOM_WEIGHTS, k=1)[0]
        channel = rng.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]
        customer_type = rng.choices(CUSTOMER_TYPES, weights=CUSTOMER_WEIGHTS, k=1)[0]
        country = rng.choices(COUNTRIES, weights=COUNTRY_WEIGHTS, k=1)[0]
        rooms_booked = rng.choices([1, 2, 3], weights=[0.90, 0.09, 0.01], k=1)[0]
        adults = rng.choices([1, 2, 3, 4], weights=[0.16, 0.62, 0.16, 0.06], k=1)[0]
        children = rng.choices([0, 1, 2], weights=[0.84, 0.11, 0.05], k=1)[0] if room_type == "Family" else rng.choices([0, 1, 2], weights=[0.95, 0.04, 0.01], k=1)[0]
        babies = int(rng.random() < 0.025)

        seasonal_factor = MONTH_RATE[arrival.month - 1]
        weekend_factor = 1.08 if arrival.weekday() in (4, 5) else 1.0
        adr = round(max(75, min(320, rng.gauss(BASE_RATES[room_type] * seasonal_factor * weekend_factor, 17))), 2)

        cancellation_chance = {
            "Online Travel Agent": 0.28,
            "Direct Website": 0.15,
            "Corporate": 0.08,
            "Offline Travel Agent": 0.19,
            "Phone": 0.14,
        }[channel]
        cancellation_chance += {"Transient": 0.03, "Contract": -0.04, "Transient-Party": 0.0, "Group": -0.02}[customer_type]
        cancellation_chance += min(0.08, lead_time / 3000)
        is_canceled = int(rng.random() < max(0.04, min(0.45, cancellation_chance)))
        weekend_nights = sum((arrival + timedelta(days=offset)).weekday() in (4, 5) for offset in range(nights))
        meal = rng.choices(["BB", "HB", "FB", "SC"], weights=[0.70, 0.16, 0.04, 0.10], k=1)[0]
        market_segment = {
            "Online Travel Agent": "Online TA",
            "Direct Website": "Direct",
            "Corporate": "Corporate",
            "Offline Travel Agent": "Offline TA/TO",
            "Phone": "Direct",
        }[channel]

        rows.append(
            {
                "booking_id": f"HB{100000 + index}",
                "booking_date": booking_date.isoformat(),
                "arrival_date": arrival.isoformat(),
                "room_type": room_type,
                "booking_channel": channel,
                "market_segment": market_segment,
                "customer_type": customer_type,
                "country": country,
                "meal": meal,
                "lead_time": lead_time,
                "stays_in_weekend_nights": weekend_nights,
                "stays_in_week_nights": nights - weekend_nights,
                "total_nights": nights,
                "adults": adults,
                "children": children,
                "babies": babies,
                "total_guests": adults + children + babies,
                "rooms_booked": rooms_booked,
                "adr": f"{adr:.2f}",
                "is_canceled": is_canceled,
                "reservation_status": "Canceled" if is_canceled else "Confirmed",
                "revenue": f"{(0 if is_canceled else adr * rooms_booked * nights):.2f}",
            }
        )
    return rows


def _inventory_rows() -> list[dict[str, object]]:
    rows = []
    capacity = {"Standard Double": 56, "Superior": 34, "Deluxe": 40, "Family": 24, "Suite": 16}
    current = date(2023, 1, 1)
    last_day = date(2025, 12, 31)
    while current <= last_day:
        season_factor = 1.0 if current.month in (6, 7, 8, 9) else 0.94
        for room_type in ROOM_TYPES:
            rows.append(
                {
                    "date": current.isoformat(),
                    "room_type": room_type,
                    "total_rooms": round(capacity[room_type] * season_factor),
                }
            )
        current += timedelta(days=1)
    return rows


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    _write_csv(DATA_DIR / "bookings.csv", BOOKING_COLUMNS, _booking_rows(rng))
    _write_csv(DATA_DIR / "room_inventory.csv", INVENTORY_COLUMNS, _inventory_rows())
    print(f"Generated {BOOKING_COUNT:,} synthetic bookings and daily room inventory in {DATA_DIR}.")


if __name__ == "__main__":
    main()