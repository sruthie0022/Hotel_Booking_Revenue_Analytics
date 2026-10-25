# Hotel Booking & Revenue Analytics

A Streamlit dashboard for exploring bookings, revenue, cancellations, guest markets, ADR, and occupancy. The included records are synthetic and are intended for demonstration and coursework, not as claims about a real hotel.

## Run in VS Code (Windows)

1. Open this project folder in VS Code.
2. Open **Terminal → New Terminal** and create a virtual environment:

	```powershell
	py -m venv .venv
	```

3. Activate it and install the project packages:

	```powershell
	.\.venv\Scripts\Activate.ps1
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt
	```

	If PowerShell blocks activation, use the environment's executable directly:

	```powershell
	.\.venv\Scripts\python.exe -m pip install -r requirements.txt
	```

4. In VS Code, run **Python: Select Interpreter** and choose `.venv`.
5. Start the dashboard:

	```powershell
	streamlit run app.py
	```

	If activation was skipped, run `\.venv\Scripts\python.exe -m streamlit run app.py` instead. Streamlit prints the local URL, normally `http://localhost:8501`.

## Run the analytics in Google Colab

Open `Hotel_Booking_Analytics_Colab.ipynb` in Google Colab and run its cells from top to bottom. When prompted, upload `Hotel_Booking_Analytics_Colab.zip` or select both CSV files individually. The ZIP contains the notebook and both data files; if opening from the ZIP, extract it first and open the `.ipynb` in Colab. The notebook displays headline metrics and Plotly charts without starting a Streamlit server.

## Dashboard

- KPIs: bookings, confirmed room revenue, room-night-weighted ADR, occupancy, cancellation rate, and confirmed guests.
- Filters: arrival dates, hotel type when supplied, room type, customer type, booking channel, country, and reservation status.
- Charts: monthly bookings/revenue, room-type revenue, channel bookings, monthly cancellations, monthly ADR, guests by country, and daily occupancy.
- Insights are recalculated from the filtered records.
- Filtered rows can be inspected in the app or downloaded as CSV.
- A Random Forest cancellation-risk model uses an 80/20 stratified holdout split and available booking attributes. It is an educational decision-support example, not a causal explanation or production prediction service.

## Included Data

`data/bookings.csv` contains 6,500 synthetic reservations covering arrival dates in 2023–2025. `data/room_inventory.csv` contains daily capacity by room type. Both files are included and work with the app directly.

The archive's booking schema uses `total_nights` rather than `departure_date`; the loader derives checkout dates as arrival date plus nights. It also includes `reservation_status`, `lead_time`, `market_segment`, guest counts, and precomputed revenue. The loader validates the dates, cancellation flags, and stay lengths before use. `data/bookings.csv` does not contain `hotel_type`; the dashboard therefore marks that dimension as unavailable instead of fabricating hotel categories. Hotel-type filtering is available when a replacement dataset supplies that column.

### Accepted booking fields

Required: `booking_id`, `arrival_date`, `room_type`, `customer_type`, `booking_channel`, `country`, `is_canceled`, `adr`, `rooms_booked`, `adults`, `children`, and `babies`, plus either `departure_date` or positive `total_nights`.

Optional fields such as `booking_date`, `lead_time`, `market_segment`, `reservation_status`, `revenue`, and `total_guests` are retained for the data view and model. If `reservation_status` is absent it is derived from `is_canceled`. If `hotel_type` is absent it is represented as unavailable.

### Accepted inventory fields

Daily room capacity is required to calculate occupancy. The loader accepts either `inventory_date` / `rooms_available` or the included file's `date` / `total_rooms`, plus `room_type`. `hotel_type` is optional. Rows must be unique per date, room type, and hotel type when present.

Occupancy is calculated as confirmed occupied room-nights divided by available room-nights over matching inventory dates and room types. A stay occupies each date from arrival up to, but not including, departure. The arrival-date filter selects reservations; their full nights are counted against the capacity calendar. Customer, channel, country, and status filters scope the numerator, so segment selections show that segment's occupied share of matching available capacity, not a standalone property occupancy rate. If the selected hotel category has no matching capacity data, occupancy is marked unavailable.

## Metric Definitions

- Revenue: `ADR × rooms booked × nights`, confirmed stays only. The dashboard recomputes it; canceled reservations contribute zero.
- ADR: confirmed revenue divided by confirmed room-nights (a room-night-weighted rate).
- Cancellation rate: canceled reservations divided by all filtered reservations.
- Total guests: adults + children + babies for confirmed reservations.
- Monthly trends are grouped by arrival month. Revenue and ADR remain in the source currency units; the dashboard does not infer or convert currency.

## Regenerate Synthetic Data

To replace both included CSV files with a new deterministic sample using the project's schema:

```powershell
python generate_data.py
```

The generator uses a fixed random seed for reproducibility. Running it overwrites `data/bookings.csv` and `data/room_inventory.csv`.

## Project Structure

```text
app.py                 Streamlit interface, charts, KPIs, and model
generate_data.py       Reproducible synthetic bookings and inventory
data/                  Included synthetic CSV files
src/data_loader.py     CSV validation and schema normalization
src/analytics.py       Filters, metrics, aggregates, occupancy, and insights
assets/                Reserved for project assets
.streamlit/config.toml Streamlit theme and server defaults
requirements.txt       Python dependencies
README.md              Setup, data schema, and metric definitions
```
# Hotel Booking & Revenue Analytics

An interactive Streamlit dashboard for exploring hotel reservations, revenue, guest markets, cancellations, ADR, and room occupancy. The included `data/bookings.csv` contains 6,500 deterministic synthetic demonstration records. Dashboard results based on this file are illustrative, not actual hotel performance; replace it with an authorized real booking export for real analysis.

## Run the dashboard

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

## Booking data

The included `data/bookings.csv` is ready to run and contains one unique reservation per row. For a real analysis, replace it with a booking-level export using the same schema. The dashboard requires these columns:

| Column | Description |
| --- | --- |
| `booking_id` | Unique, non-empty reservation identifier |
| `arrival_date` | Check-in date (`YYYY-MM-DD`); date filters use this date |
| `departure_date` | Check-out date (`YYYY-MM-DD`), later than arrival; checkout day is not an occupied night |
| `hotel_type` | Property or hotel category |
| `room_type` | Reserved room category |
| `customer_type` | Customer segment |
| `booking_channel` | Reservation channel |
| `country` | Guest country or country code |
| `is_canceled` | Boolean, `0`/`1`, or a supported text status such as `canceled`/`confirmed` |
| `adr` | Nightly rate per room, in a single consistent currency |
| `rooms_booked` | Number of rooms in the reservation; must be greater than zero |
| `adults`, `children`, `babies` | Non-negative guest counts; include all three columns |

The ten requested project fields are included, along with `rooms_booked`, `adults`, `children`, and `babies`, which the current dashboard uses for room-night revenue, guest totals, and its KPIs. These four support columns are required by the existing loader.

Revenue is calculated for confirmed reservations as `adr × rooms_booked × nights`. The ADR KPI is weighted by room-nights. Revenue and ADR remain in the source currency units; no currency is inferred or converted. Total bookings and cancellation rate include canceled reservations; guest totals and revenue include confirmed reservations only. Monthly trends are grouped by arrival month.

## Occupancy inventory (optional)

Occupancy cannot be derived reliably from booking rows alone. To enable it, save a daily room inventory export as `data/room_inventory.csv` with these columns:

| Column | Description |
| --- | --- |
| `inventory_date` | Calendar date for the capacity record |
| `hotel_type` | Must use the same values as the bookings file |
| `room_type` | Must use the same values as the bookings file |
| `rooms_available` | Positive room capacity for that date and category |

There must be one row per date, hotel type, and room type. Occupancy is confirmed room-nights divided by matching available room-nights across the full stays of reservations whose arrival dates match the selected date range. Hotel and room filters scope both sides; customer, channel, and country filters scope the occupied room-nights, so those segment filters represent that segment's share of matching inventory capacity.

If the booking file is missing, the app displays the schema instead of analytics. If only the optional inventory file is missing, booking, revenue, cancellation, and guest analyses remain available while occupancy is marked unavailable.

## Project structure

```text
app.py                 Streamlit interface and visualizations
data/                  Synthetic sample bookings; optional room inventory
src/data_loader.py     CSV schema validation and normalization
src/analytics.py       Filtering, KPIs, aggregation, and insights
assets/                Reserved for project assets
requirements.txt       Python dependencies
README.md              Setup and data documentation
```