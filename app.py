"""Interactive hotel booking and revenue analytics dashboard."""

from pathlib import Path

import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px

try:
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder
except (ImportError, OSError) as error:
    ML_IMPORT_ERROR = error
else:
    ML_IMPORT_ERROR = None

from src.analytics import (
    apply_filters,
    build_business_insights,
    calculate_kpis,
    monthly_adr,
    monthly_bookings,
    monthly_cancellations,
    monthly_occupancy,
    monthly_revenue,
    revenue_by_room_type,
    bookings_by_channel,
    guests_by_country,
)
from src.data_loader import load_bookings, load_inventory


BASE_DIR = Path(__file__).resolve().parent
BOOKINGS_PATH = BASE_DIR / "data" / "bookings.csv"
INVENTORY_PATH = BASE_DIR / "data" / "room_inventory.csv"

st.set_page_config(
    page_title="Staywise | Hotel Analytics",
    page_icon="H",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
    :root {
        --ink: #ecf7f4;
        --muted: #9eb7b0;
        --paper: #0b1220;
        --panel: #111c2d;
        --panel-strong: #152338;
        --line: rgba(255,255,255,0.08);
        --green: #3dd7b0;
        --teal: #72d6ff;
        --coral: #ff8a65;
        --shadow: rgba(0,0,0,0.28);
    }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp { background: linear-gradient(180deg, #07111b 0%, #0d1726 100%); color: var(--ink); }
    h1, h2, h3 { font-family: 'Manrope', sans-serif; color: var(--ink); }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }
    [data-testid="stSidebar"] { background: #0d1726; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] * { color: var(--ink); }
    [data-testid="stSidebar"] .stMarkdownContainer,
    [data-testid="stSidebar"] .stSelectbox,
    [data-testid="stSidebar"] .stMultiSelect,
    [data-testid="stSidebar"] .stDateInput,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] .st-emotion-cache-1h9usn1,
    [data-testid="stSidebar"] .st-emotion-cache-1v0mbdj {
        color: var(--ink) !important;
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stDateInput label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stCheckbox label,
    [data-testid="stSidebar"] .stRadio label {
        color: #c9d3d0 !important;
    }
    [data-testid="stSidebar"] .stMarkdownContainer p,
    [data-testid="stSidebar"] .stMarkdownContainer div,
    [data-testid="stSidebar"] .st-bx,
    [data-testid="stSidebar"] .st-c7 {
        color: var(--ink) !important;
    }
    [data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(17,28,45,0.96), rgba(13,23,38,0.97));
        border: 1px solid var(--line); border-radius: 12px;
        box-shadow: 0 10px 30px var(--shadow); padding: 16px 18px; min-height: 112px;
    }
    [data-testid="stMetricLabel"] { color: var(--muted); font-size: 0.84rem; }
    [data-testid="stMetricValue"] { color: var(--ink); font-family: 'Manrope', sans-serif; }
    .eyebrow { color: var(--green); font-weight: 700; letter-spacing: 0.08em; font-size: 0.72rem; text-transform: uppercase; }
    .subtitle { color: var(--muted); margin-top: -0.6rem; margin-bottom: 1.5rem; }
    .section-title { font-family: 'Manrope', sans-serif; font-size: 1.05rem; font-weight: 700; margin: 0.8rem 0 0.2rem; color: var(--ink); }
    .insight-box { background: rgba(17,28,45,0.9); border-left: 4px solid var(--green); border-radius: 4px; padding: 13px 16px; margin: 8px 0; color: var(--ink); }
    div[data-testid="stDownloadButton"] button { border-color: var(--green); color: var(--green); }
    .stDataFrame { background: transparent; }
    .stTabs [role="tablist"] { background: rgba(17,28,45,0.8); border-radius: 10px; }
    .stTabs [role="tab"] { color: var(--muted); }
    .stTabs [role="tab"][aria-selected="true"] { color: var(--ink); background: rgba(61,215,176,0.12); }
    </style>
    """,
    unsafe_allow_html=True,
)


def money(value: float) -> str:
    return f"{value:,.2f}"


def plot_layout(fig, height: int = 330):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin=dict(l=12, r=12, t=24, b=12),
        font=dict(family="DM Sans, sans-serif", color="#ecf7f4"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="",
        legend=dict(font=dict(color="#ecf7f4")),
    )
    fig.update_xaxes(showgrid=False, linecolor="rgba(255,255,255,0.15)", tickfont=dict(color="#dfece9"))
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)", zeroline=False, tickfont=dict(color="#dfece9"))
    return fig


st.sidebar.markdown("<div class='eyebrow'>STAYWISE / ANALYTICS</div>", unsafe_allow_html=True)
st.sidebar.title("Dashboard filters")

if not BOOKINGS_PATH.exists():
    st.markdown("<div class='eyebrow'>HOTEL BOOKING & REVENUE ANALYTICS</div>", unsafe_allow_html=True)
    st.title("Your hotel performance, clearly in view.")
    st.markdown(
        "Add your booking export to `data/bookings.csv` to begin. No sample data or "
        "placeholder results are displayed. The exact schema and optional inventory "
        "file are documented below and in the README."
    )
    st.subheader("Required: `data/bookings.csv`")
    st.dataframe(
        pd.DataFrame(
            [
                ("booking_id", "Unique reservation identifier"),
                ("arrival_date", "Check-in date, YYYY-MM-DD"),
                ("departure_date or total_nights", "Check-out date, or positive stay length in nights"),
                ("hotel_type (optional)", "Hotel/property category; not present in the included dataset"),
                ("room_type", "Reserved room category"),
                ("customer_type", "Customer segment"),
                ("booking_channel", "Channel used to make the reservation"),
                ("country", "Guest country code or name"),
                ("is_canceled", "Boolean or 0/1 cancellation status"),
                ("adr", "Average nightly rate per room, in one consistent currency"),
                ("rooms_booked", "Number of rooms in the reservation"),
                ("adults / children / babies", "Guest counts; provide all three columns"),
            ],
            columns=["Column", "Meaning"],
        ),
        hide_index=True,
        width="stretch",
    )
    st.info(
        "Occupancy needs `data/room_inventory.csv` with `room_type`, a date column "
        "(`inventory_date` or `date`), and capacity (`rooms_available` or `total_rooms`). "
        "`hotel_type` is optional. "
        "Without inventory, occupancy is shown as unavailable rather than estimated."
    )
    st.stop()

try:
    bookings = load_bookings(BOOKINGS_PATH)
    inventory = load_inventory(INVENTORY_PATH) if INVENTORY_PATH.exists() else None
except (ValueError, OSError) as error:
    st.error(f"Could not load the hotel data: {error}")
    st.stop()

if bookings.empty:
    st.warning("The bookings file has no records yet. Add booking rows to see analytics.")
    st.stop()

date_min = bookings["arrival_date"].min().date()
date_max = bookings["arrival_date"].max().date()
selected_dates = st.sidebar.date_input(
    "Arrival date range",
    value=(date_min, date_max),
    min_value=date_min,
    max_value=date_max,
)

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = end_date = selected_dates

def multiselect_filter(label: str, column: str) -> list[str]:
    if column == "hotel_type" and bookings[column].eq("Not provided").all():
        st.sidebar.caption("Hotel type is not included in this dataset.")
        return []
    values = sorted(bookings[column].dropna().astype(str).unique().tolist())
    return st.sidebar.multiselect(label, values, default=[])


selected_filters = {
    "start_date": start_date,
    "end_date": end_date,
    "hotel_type": multiselect_filter("Hotel type", "hotel_type"),
    "room_type": multiselect_filter("Room type", "room_type"),
    "customer_type": multiselect_filter("Customer type", "customer_type"),
    "booking_channel": multiselect_filter("Booking channel", "booking_channel"),
    "country": multiselect_filter("Country", "country"),
    "reservation_status": multiselect_filter("Reservation status", "reservation_status"),
}
filtered = apply_filters(bookings, selected_filters)

st.markdown("<div class='eyebrow'>HOTEL BOOKING & REVENUE ANALYTICS</div>", unsafe_allow_html=True)
st.title("Performance overview")
st.markdown(
    f"<div class='subtitle'>Arrival dates: {start_date:%b %d, %Y} to {end_date:%b %d, %Y} "
    f"&nbsp;·&nbsp; {len(filtered):,} matching reservations</div>",
    unsafe_allow_html=True,
)

occupancy_frame = monthly_occupancy(filtered, inventory, selected_filters)
kpis = calculate_kpis(filtered, occupancy_frame)

metric_columns = st.columns(6)
metric_columns[0].metric("Total bookings", f"{kpis['total_bookings']:,}")
metric_columns[1].metric("Total revenue", money(kpis["total_revenue"]))
metric_columns[2].metric("Average daily rate", money(kpis["adr"]))
metric_columns[3].metric(
    "Occupancy rate",
    f"{kpis['occupancy_rate']:.1%}" if kpis["occupancy_rate"] is not None else "N/A",
    help="Occupied room-nights divided by matching available room-nights. Requires room_inventory.csv.",
)
metric_columns[4].metric("Cancellation rate", f"{kpis['cancellation_rate']:.1%}")
metric_columns[5].metric("Total guests", f"{kpis['total_guests']:,}")

st.markdown("<div class='section-title'>Booking and revenue trends</div>", unsafe_allow_html=True)
left, right = st.columns(2)
with left:
    st.caption("Monthly bookings")
    trend = monthly_bookings(filtered)
    st.plotly_chart(
        plot_layout(px.line(trend, x="month", y="bookings", markers=True, color_discrete_sequence=["#167d66"])),
        width="stretch",
    )
with right:
    st.caption("Monthly revenue")
    trend = monthly_revenue(filtered)
    st.plotly_chart(
        plot_layout(px.bar(trend, x="month", y="revenue", color_discrete_sequence=["#db7357"])),
        width="stretch",
    )

st.markdown("<div class='section-title'>Revenue and booking mix</div>", unsafe_allow_html=True)
left, right = st.columns(2)
with left:
    st.caption("Revenue by room type")
    chart_data = revenue_by_room_type(filtered)
    st.plotly_chart(
        plot_layout(px.bar(chart_data, x="revenue", y="room_type", orientation="h", color_discrete_sequence=["#167d66"])),
        width="stretch",
    )
with right:
    st.caption("Bookings by channel")
    chart_data = bookings_by_channel(filtered)
    st.plotly_chart(
        plot_layout(px.bar(chart_data, x="bookings", y="booking_channel", orientation="h", color_discrete_sequence=["#3586a3"])),
        width="stretch",
    )

st.markdown("<div class='section-title'>Cancellation and rate performance</div>", unsafe_allow_html=True)
left, right = st.columns(2)
with left:
    st.caption("Monthly cancellation analysis")
    chart_data = monthly_cancellations(filtered)
    st.plotly_chart(
        plot_layout(px.bar(chart_data, x="month", y="bookings", color="status", barmode="stack",
                           color_discrete_map={"Confirmed": "#167d66", "Canceled": "#db7357"})),
        width="stretch",
    )
with right:
    st.caption("Average daily rate by month")
    chart_data = monthly_adr(filtered)
    st.plotly_chart(
        plot_layout(px.line(chart_data, x="month", y="adr", markers=True, color_discrete_sequence=["#3586a3"])),
        width="stretch",
    )

st.markdown("<div class='section-title'>Guest markets and occupancy</div>", unsafe_allow_html=True)
left, right = st.columns(2)
with left:
    st.caption("Guests by country · top 10")
    chart_data = guests_by_country(filtered)
    st.plotly_chart(
        plot_layout(px.bar(chart_data, x="guests", y="country", orientation="h", color_discrete_sequence=["#db7357"])),
        width="stretch",
    )
with right:
    st.caption("Daily occupancy trend")
    if inventory is None:
        st.info("Add `data/room_inventory.csv` to calculate occupancy from actual room capacity.")
    elif occupancy_frame.empty:
        st.info("No matching inventory records are available for this selection.")
    else:
        st.plotly_chart(
            plot_layout(px.line(occupancy_frame, x="date", y="occupancy_rate", markers=True,
                                labels={"occupancy_rate": "Occupancy", "date": "Date"},
                                color_discrete_sequence=["#167d66"])),
            width="stretch",
        )

st.markdown("<div class='section-title'>Business insights</div>", unsafe_allow_html=True)
insights = build_business_insights(filtered, kpis, occupancy_frame)
if not insights:
    st.info("No business insights are available for the current filters.")
else:
    for insight in insights:
        st.markdown(f"<div class='insight-box'>{insight}</div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'>Cancellation risk model</div>", unsafe_allow_html=True)
st.caption("Random Forest estimates cancellation risk from the available booking attributes. Treat it as decision support, not an automatic decision.")

candidate_features = [
    "lead_time", "total_nights", "adr", "rooms_booked", "adults", "children", "babies",
    "booking_channel", "room_type", "market_segment", "customer_type", "country", "hotel_type",
]
model_features = [column for column in candidate_features if column in bookings.columns]
categorical_features = [
    column for column in ["booking_channel", "room_type", "market_segment", "customer_type", "country", "hotel_type"]
    if column in model_features
]
numeric_features = [column for column in model_features if column not in categorical_features]
model_data = bookings.dropna(subset=["is_canceled", *model_features]).copy()
class_counts = model_data["is_canceled"].value_counts()

if ML_IMPORT_ERROR is not None:
    st.info(
        "Cancellation-risk modeling is unavailable in this Python environment because "
        f"a scikit-learn dependency could not load: {ML_IMPORT_ERROR}"
    )
elif len(model_data) < 20 or len(class_counts) < 2 or class_counts.min() < 2:
    st.info("At least 20 bookings and two examples of each cancellation outcome are needed to train the model.")
else:
    model_data["is_canceled"] = model_data["is_canceled"].astype(int)
    model_input = model_data[model_features].copy()
    for column in categorical_features:
        model_input[column] = model_input[column].fillna("Unknown").astype(str)

    preprocessor = ColumnTransformer(
        [
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("numeric", "passthrough", numeric_features),
        ]
    )
    classifier = Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=160,
                    max_depth=10,
                    random_state=42,
                    class_weight="balanced",
                    n_jobs=-1,
                ),
            ),
        ]
    )
    x_train, x_test, y_train, y_test = train_test_split(
        model_input,
        model_data["is_canceled"],
        test_size=0.2,
        random_state=42,
        stratify=model_data["is_canceled"],
    )
    classifier.fit(x_train, y_train)
    predictions = classifier.predict(x_test)
    model_metric, feature_metric = st.columns(2)
    model_metric.metric("Holdout accuracy", f"{accuracy_score(y_test, predictions):.1%}")
    feature_metric.metric("Training records", f"{len(x_train):,}")
    st.code(classification_report(y_test, predictions, zero_division=0), language="text")

    score_rows = filtered.head(25).copy()
    if not score_rows.empty:
        score_input = score_rows[model_features].copy()
        for column in categorical_features:
            score_input[column] = score_input[column].fillna("Unknown").astype(str)
        score_rows["predicted_cancellation_risk"] = classifier.predict_proba(score_input)[:, 1]
        score_rows["risk"] = np.select(
            [score_rows["predicted_cancellation_risk"] >= 0.65, score_rows["predicted_cancellation_risk"] >= 0.35],
            ["High", "Medium"],
            default="Low",
        )
        st.dataframe(
            score_rows.sort_values("predicted_cancellation_risk", ascending=False),
            width="stretch",
            hide_index=True,
        )

st.divider()
st.download_button(
    "Download filtered bookings as CSV",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="hotel_bookings_filtered.csv",
    mime="text/csv",
    width="content",
)
with st.expander(f"View filtered bookings ({len(filtered):,})"):
    st.dataframe(filtered, width="stretch", hide_index=True)
st.caption(
    "Revenue is calculated for non-canceled reservations as ADR × rooms booked × nights. "
    "Guest totals include confirmed reservations only. Revenue and ADR use the source currency units."
)