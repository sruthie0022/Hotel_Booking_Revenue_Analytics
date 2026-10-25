"""Filter, aggregate, and derive hotel booking performance measures."""

from collections.abc import Mapping

import pandas as pd


def apply_filters(bookings: pd.DataFrame, filters: Mapping) -> pd.DataFrame:
    """Apply arrival-date and categorical filters to booking rows."""
    mask = bookings["arrival_date"].between(
        pd.Timestamp(filters["start_date"]), pd.Timestamp(filters["end_date"])
    )
    for column in ["hotel_type", "room_type", "customer_type", "booking_channel", "country", "reservation_status"]:
        selected = filters.get(column, [])
        if selected:
            mask &= bookings[column].astype(str).isin(selected)
    return bookings.loc[mask].copy()


def _confirmed(bookings: pd.DataFrame) -> pd.DataFrame:
    return bookings.loc[~bookings["is_canceled"]]


def _room_nights(bookings: pd.DataFrame) -> pd.Series:
    nights = (bookings["departure_date"] - bookings["arrival_date"]).dt.days
    return nights * bookings["rooms_booked"]


def calculate_kpis(bookings: pd.DataFrame, occupancy: pd.DataFrame) -> dict[str, float | int | None]:
    """Calculate headline metrics using confirmed stays where appropriate."""
    confirmed = _confirmed(bookings)
    room_nights = _room_nights(confirmed)
    denominator = float(room_nights.sum())
    revenue = float((confirmed["adr"] * room_nights).sum())
    occupancy_rate = None
    if not occupancy.empty:
        available = float(occupancy["rooms_available"].sum())
        if available > 0:
            occupancy_rate = float(occupancy["rooms_occupied"].sum() / available)

    booking_count = len(bookings)
    return {
        "total_bookings": booking_count,
        "total_revenue": revenue,
        "adr": float((confirmed["adr"] * room_nights).sum() / denominator) if denominator else 0.0,
        "occupancy_rate": occupancy_rate,
        "cancellation_rate": float(bookings["is_canceled"].mean()) if booking_count else 0.0,
        "total_guests": int(confirmed[["adults", "children", "babies"]].sum().sum()),
    }


def monthly_bookings(bookings: pd.DataFrame) -> pd.DataFrame:
    data = bookings.assign(month=bookings["arrival_date"].dt.to_period("M").dt.to_timestamp())
    return data.groupby("month", as_index=False).size().rename(columns={"size": "bookings"})


def monthly_revenue(bookings: pd.DataFrame) -> pd.DataFrame:
    data = _confirmed(bookings).copy()
    data["revenue"] = data["adr"] * _room_nights(data)
    data["month"] = data["arrival_date"].dt.to_period("M").dt.to_timestamp()
    return data.groupby("month", as_index=False)["revenue"].sum()


def revenue_by_room_type(bookings: pd.DataFrame) -> pd.DataFrame:
    data = _confirmed(bookings).copy()
    data["revenue"] = data["adr"] * _room_nights(data)
    return data.groupby("room_type", as_index=False)["revenue"].sum().sort_values("revenue")


def bookings_by_channel(bookings: pd.DataFrame) -> pd.DataFrame:
    return (
        bookings.groupby("booking_channel", as_index=False)
        .size()
        .rename(columns={"size": "bookings"})
        .sort_values("bookings")
    )


def monthly_cancellations(bookings: pd.DataFrame) -> pd.DataFrame:
    data = bookings.assign(
        month=bookings["arrival_date"].dt.to_period("M").dt.to_timestamp(),
        status=bookings["is_canceled"].map({True: "Canceled", False: "Confirmed"}),
    )
    return data.groupby(["month", "status"], as_index=False).size().rename(columns={"size": "bookings"})


def monthly_adr(bookings: pd.DataFrame) -> pd.DataFrame:
    data = _confirmed(bookings).copy()
    data["room_nights"] = _room_nights(data)
    data["weighted_adr"] = data["adr"] * data["room_nights"]
    data["month"] = data["arrival_date"].dt.to_period("M").dt.to_timestamp()
    result = data.groupby("month", as_index=False).agg(
        weighted_adr=("weighted_adr", "sum"), room_nights=("room_nights", "sum")
    )
    result["adr"] = result["weighted_adr"] / result["room_nights"]
    return result[["month", "adr"]]


def guests_by_country(bookings: pd.DataFrame) -> pd.DataFrame:
    data = _confirmed(bookings).copy()
    data["guests"] = data[["adults", "children", "babies"]].sum(axis=1)
    return (
        data.groupby("country", as_index=False)["guests"]
        .sum()
        .nlargest(10, "guests")
        .sort_values("guests")
    )


def monthly_occupancy(
    bookings: pd.DataFrame,
    inventory: pd.DataFrame | None,
    filters: Mapping,
) -> pd.DataFrame:
    """Calculate daily occupied/available room share; return empty without inventory."""
    columns = ["date", "rooms_occupied", "rooms_available", "occupancy_rate"]
    if inventory is None or inventory.empty:
        return pd.DataFrame(columns=columns)

    confirmed = _confirmed(bookings)
    if confirmed.empty:
        return pd.DataFrame(columns=columns)
    if filters.get("hotel_type") and inventory["hotel_type"].eq("Not provided").all():
        return pd.DataFrame(columns=columns)
    stay_start = pd.Timestamp(filters["start_date"])
    stay_end = max(
        pd.Timestamp(filters["end_date"]),
        confirmed["departure_date"].max() - pd.Timedelta(days=1),
    )
    inventory_rows = inventory.loc[
        inventory["inventory_date"].between(stay_start, stay_end)
    ].copy()
    for column in ["hotel_type", "room_type"]:
        selected = filters.get(column, [])
        if selected:
            inventory_rows = inventory_rows.loc[inventory_rows[column].isin(selected)]
    capacity = inventory_rows.groupby("inventory_date", as_index=False)["rooms_available"].sum()
    if capacity.empty:
        return pd.DataFrame(columns=columns)

    stays: list[tuple[pd.Timestamp, float]] = []
    for row in confirmed.itertuples(index=False):
        occupied_dates = pd.date_range(row.arrival_date, row.departure_date - pd.Timedelta(days=1), freq="D")
        stays.extend((stay_date, float(row.rooms_booked)) for stay_date in occupied_dates)
    occupied = pd.DataFrame(stays, columns=["date", "rooms_occupied"])
    if not occupied.empty:
        occupied = occupied.groupby("date", as_index=False)["rooms_occupied"].sum()

    result = capacity.rename(columns={"inventory_date": "date"}).merge(occupied, on="date", how="left")
    result["rooms_occupied"] = result["rooms_occupied"].fillna(0.0)
    result["occupancy_rate"] = result["rooms_occupied"] / result["rooms_available"]
    return result[columns].sort_values("date")


def build_business_insights(
    bookings: pd.DataFrame,
    kpis: Mapping,
    occupancy: pd.DataFrame,
) -> list[str]:
    """Summarize notable patterns derived only from the currently filtered data."""
    if bookings.empty:
        return []

    insights: list[str] = []
    channels = bookings_by_channel(bookings)
    if not channels.empty:
        top_channel = channels.iloc[-1]
        share = float(top_channel["bookings"] / len(bookings))
        insights.append(
            f"{top_channel['booking_channel']} is the leading booking channel, "
            f"accounting for {share:.1%} of filtered reservations."
        )

    revenue = monthly_revenue(bookings)
    if not revenue.empty:
        peak = revenue.loc[revenue["revenue"].idxmax()]
        insights.append(
            f"The highest-revenue arrival month is {peak['month']:%B %Y} "
            f"at {peak['revenue']:,.2f} in the source currency units."
        )

    if kpis["cancellation_rate"] > 0:
        insights.append(
            f"{kpis['cancellation_rate']:.1%} of filtered reservations were canceled "
            "before arrival; review cancellation patterns by channel and customer mix."
        )
    elif len(bookings):
        insights.append("No cancellations appear in the current filtered booking records.")

    if not occupancy.empty:
        average_occupancy = kpis["occupancy_rate"]
        peak_day = occupancy.loc[occupancy["occupancy_rate"].idxmax()]
        insights.append(
            f"Matching inventory averaged {average_occupancy:.1%} occupancy; "
            f"the busiest inventory date was {peak_day['date']:%b %d, %Y} "
            f"at {peak_day['occupancy_rate']:.1%}."
        )
    return insights