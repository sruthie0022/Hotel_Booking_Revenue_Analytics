"""CSV loading, schema validation, and basic data normalization."""

from pathlib import Path

import pandas as pd


BOOKING_COLUMNS = {
    "booking_id",
    "arrival_date",
    "room_type",
    "customer_type",
    "booking_channel",
    "country",
    "is_canceled",
    "adr",
    "rooms_booked",
    "adults",
    "children",
    "babies",
}
INVENTORY_COLUMNS = {"inventory_date", "hotel_type", "room_type", "rooms_available"}


def _require_columns(data: pd.DataFrame, required: set[str], source: Path) -> None:
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"{source.name} is missing required columns: {', '.join(missing)}")


def _parse_dates(data: pd.DataFrame, column: str, source: Path) -> None:
    parsed = pd.to_datetime(data[column], errors="coerce")
    invalid_count = int(parsed.isna().sum())
    if invalid_count:
        raise ValueError(f"{source.name} has {invalid_count} invalid or empty `{column}` value(s).")
    data[column] = parsed.dt.normalize()


def _parse_cancellation_status(values: pd.Series, source: Path) -> pd.Series:
    normalized = values.astype(str).str.strip().str.lower()
    mapping = {
        "1": True,
        "true": True,
        "yes": True,
        "canceled": True,
        "cancelled": True,
        "0": False,
        "false": False,
        "no": False,
        "confirmed": False,
        "not canceled": False,
        "not cancelled": False,
    }
    result = normalized.map(mapping)
    if result.isna().any():
        examples = ", ".join(normalized[result.isna()].drop_duplicates().head(3))
        raise ValueError(f"{source.name} has unsupported is_canceled value(s): {examples}")
    return result.astype(bool)


def _parse_numeric_columns(data: pd.DataFrame, columns: list[str], source: Path) -> None:
    for column in columns:
        values = pd.to_numeric(data[column], errors="coerce")
        if values.isna().any():
            raise ValueError(f"{source.name} has missing or non-numeric values in `{column}`.")
        if (values < 0).any():
            raise ValueError(f"{source.name} contains negative values in `{column}`.")
        data[column] = values


def load_bookings(path: str | Path) -> pd.DataFrame:
    """Load and validate booking-level data from CSV."""
    source = Path(path)
    data = pd.read_csv(source)
    data.columns = data.columns.str.strip()
    _require_columns(data, BOOKING_COLUMNS, source)

    if "departure_date" not in data.columns and "total_nights" not in data.columns:
        raise ValueError(f"{source.name} needs either departure_date or total_nights.")

    if data["booking_id"].isna().any() or data["booking_id"].duplicated().any():
        raise ValueError(f"{source.name} requires a unique, non-empty booking_id for every row.")

    _parse_dates(data, "arrival_date", source)
    if "departure_date" in data.columns:
        _parse_dates(data, "departure_date", source)
        derived_nights = (data["departure_date"] - data["arrival_date"]).dt.days
        if "total_nights" in data.columns:
            _parse_numeric_columns(data, ["total_nights"], source)
            if (data["total_nights"] <= 0).any() or not data["total_nights"].eq(derived_nights).all():
                raise ValueError("total_nights must match the dates between arrival_date and departure_date.")
        else:
            data["total_nights"] = derived_nights
    else:
        _parse_numeric_columns(data, ["total_nights"], source)
        if (data["total_nights"] <= 0).any():
            raise ValueError("total_nights must be greater than zero for every reservation.")
        data["departure_date"] = data["arrival_date"] + pd.to_timedelta(data["total_nights"], unit="D")
    if (data["departure_date"] <= data["arrival_date"]).any():
        raise ValueError("Each departure_date must be later than its arrival_date.")

    data["is_canceled"] = _parse_cancellation_status(data["is_canceled"], source)
    _parse_numeric_columns(data, ["adr", "rooms_booked", "adults", "children", "babies"], source)
    for column in ["lead_time", "stays_in_weekend_nights", "stays_in_week_nights", "total_guests"]:
        if column in data.columns:
            _parse_numeric_columns(data, [column], source)
    if {"stays_in_weekend_nights", "stays_in_week_nights"}.issubset(data.columns):
        component_nights = data["stays_in_weekend_nights"] + data["stays_in_week_nights"]
        if not component_nights.eq(data["total_nights"]).all():
            raise ValueError("Weekend and weeknight counts must add up to total_nights.")
    if (data["rooms_booked"] <= 0).any():
        raise ValueError("rooms_booked must be greater than zero for every reservation.")
    if "reservation_status" not in data.columns:
        data["reservation_status"] = data["is_canceled"].map({True: "Canceled", False: "Confirmed"})

    if "hotel_type" not in data.columns:
        data["hotel_type"] = "Not provided"
    for column in ["hotel_type", "room_type", "customer_type", "booking_channel", "country"]:
        data[column] = data[column].fillna("Unknown").astype(str).str.strip()
        data.loc[data[column].eq(""), column] = "Unknown"
    return data


def load_inventory(path: str | Path) -> pd.DataFrame:
    """Load optional daily room-capacity data for occupancy calculations."""
    source = Path(path)
    data = pd.read_csv(source)
    data.columns = data.columns.str.strip()
    if "inventory_date" not in data.columns and "date" in data.columns:
        data = data.rename(columns={"date": "inventory_date"})
    if "rooms_available" not in data.columns and "total_rooms" in data.columns:
        data = data.rename(columns={"total_rooms": "rooms_available"})
    if "hotel_type" not in data.columns:
        data["hotel_type"] = "Not provided"
    _require_columns(data, INVENTORY_COLUMNS, source)
    _parse_dates(data, "inventory_date", source)
    _parse_numeric_columns(data, ["rooms_available"], source)
    if (data["rooms_available"] <= 0).any():
        raise ValueError("rooms_available must be greater than zero for each inventory row.")

    for column in ["hotel_type", "room_type"]:
        data[column] = data[column].fillna("Unknown").astype(str).str.strip()
    keys = ["inventory_date", "hotel_type", "room_type"]
    if data.duplicated(keys).any():
        raise ValueError(
            "room_inventory.csv must contain only one row per inventory_date, hotel_type, and room_type."
        )
    return data