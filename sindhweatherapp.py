import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
import datetime
import numpy as np
import plotly.express as px
import ee
import calendar as calender

# -----------------------------
# 0. Setup Earth Engine (GEE)
# -----------------------------
PROJECT_ID = st.secrets["GEE_PROJECT_ID"]
try:
    ee.Initialize(project=PROJECT_ID)
except Exception as e:
    st.error(f"GEE init failed: {e}")
    st.stop()

# -----------------------------
# 1. Load Sindh GeoJSON + Indus River
# -----------------------------
SINDH_PATH = sindh_with_indus_sea.geojson"
RIVER_PATH = Indus River Shapefiles (1)" 

sindh_gdf = gpd.read_file(SINDH_PATH)

try:
    river_gdf = gpd.read_file(RIVER_PATH)
except:
    river_gdf = None

st.title("Sindh Weather, Crops & Flood Dashboard 🌾🌧️🔥")

# -----------------------------
# 2. District Name Fix Mapping
# -----------------------------
DISTRICT_NAME_MAP = {
    "Nawabshah": "Shaheed Benazirabad",
    "Thatta": "Thatta",
    "Jacobabad": "Jacobabad",
    "Sukkur": "Sukkur",
    "Larkana": "Larkana",
    "Badin": "Badin",
    "Mirpurkhas": "Mirpur Khas",
    "Hyderabad": "Hyderabad",
    "Karachi": "Karachi",
    "Shikarpur": "Shikarpur",
    "Kashmore": "Kashmore",
    "Umerkot": "Umarkot",
    "Sanghar": "Sanghar"
}

# -----------------------------
# 3. Sidebar Options
# -----------------------------
st.sidebar.header("Controls")
selected_crop = st.sidebar.selectbox("Select Crop", ["Wheat", "Rice", "Cotton", "Sugarcane"])
year = st.sidebar.selectbox("Select Year", list(range(2020, datetime.date.today().year + 1)))
month = st.sidebar.slider("Month", 1, 12, datetime.date.today().month)

# -----------------------------
# Sowing Season Advisory
# -----------------------------
SOWING_WINDOWS = {
    "Wheat": [11, 12],       # Nov-Dec
    "Rice": [6, 7],          # Jun-Jul
    "Cotton": [4, 5],        # Apr-May
    "Sugarcane": [2, 3]      # Feb-Mar
}

current_month = datetime.date.today().month
current_year = datetime.date.today().year
sowing_months = SOWING_WINDOWS[selected_crop]

if current_month in sowing_months:
    sowing_message = (f"This month({calender.month_name[current_month]} {current_year}) "
    f"is suitabe for sowing **{selected_crop}**." 
    )
else:
    # Find next available sowing month
    future_months = [m for m in sowing_months if m > current_month]
    if future_months:
        next_month = future_months[0]
        sowing_message = f"⚠ Not sowing season now. Next sowing for **{selected_crop}** in: {calender.month_name[next_month]} {current_year}."
    else:
        next_month = sowing_months[0]
        sowing_message = f"❌ Not sowing season now. Next sowing for **{selected_crop}** will be in: {calender.month_name[next_month]} {current_year}."

st.sidebar.markdown(f"### 🌱 Sowing Advisory\n{sowing_message}")

# -----------------------------
# 4. Locations Dictionary
# -----------------------------
locations = {
    "Karachi": (24.8607, 67.0011),
    "Hyderabad": (25.3960, 68.3578),
    "Sukkur": (27.7139, 68.8356),
    "Larkana": (27.5600, 68.2264),
    "Thatta": (24.7466, 67.9235),
    "Nawabshah": (26.2483, 68.4096),
    "Mirpurkhas": (25.5251, 69.0159),
    "Badin": (24.6550, 68.8370),
    "Jacobabad": (28.2819, 68.4370),
    "Shikarpur": (27.9556, 68.6382),
    "Kashmore": (28.4329, 69.5814),
    "Umerkot": (25.3610, 69.7360),
    "Sanghar": (26.0469, 68.9492)
}

# -----------------------------
# 5. Weather Forecast API
# -----------------------------
def fetch_forecast(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,"
        f"precipitation_sum,windspeed_10m_max"
        f"&forecast_days=7&timezone=auto"
    )
    r = requests.get(url, timeout=30)
    return r.json() if r.status_code == 200 else {}

# -----------------------------
# 6. FAO Yield Data (for Popups & Charts)
# -----------------------------
FAO_YIELD = {
    "Wheat": {"Thatta": 2.5, "Nawabshah": 3.0, "Sukkur": 2.8},
    "Rice": {"Thatta": 3.5, "Badin": 3.0, "Larkana": 3.8},
    "Cotton": {"Mirpurkhas": 2.2, "Hyderabad": 2.5, "Nawabshah": 2.3},
    "Sugarcane": {"Badin": 60, "Thatta": 65, "Sanghar": 70, "Nawabshah": 68}
}

# -----------------------------
# 8. Map Setup (Locked to Sindh)
# -----------------------------
bounds = sindh_gdf.total_bounds
sindh_geom = ee.Geometry(sindh_gdf.geometry.unary_union.__geo_interface__)  # clip NDVI/SMAP/Flood

m = folium.Map(
    location=[25.5, 68.5],
    zoom_start=6,
    min_zoom=6,
    max_bounds=True,
    max_lat=bounds[3], min_lat=bounds[1],
    max_lon=bounds[2], min_lon=bounds[0],
    control_scale=True,
    prefer_canvas=True,
    attributionControl=True,
    attr='Data:MODIS NDVI,NASA SMAP,ECMWF ERA5,FAO Crop Yield | Map: OpenStreetMap contributors'
)

# Style Leaflet credits position and visibility
m.get_root().html.add_child(folium.Element("""
    <style>
        .leaflet-control-attribution {
            bottom: 0 !important;
            left: 0 !important;
            right: auto !important;
            background: rgba(255,255,255,0.85);
            font-size: 12px;
            padding: 2px 6px;
            border-radius: 3px;
        }
    </style>
"""))

# Sidebar checkboxes for overlays
st.sidebar.subheader("🛰️ Map Overlays")
show_ndvi = st.sidebar.checkbox("🌿 Show NDVI Vegetation", value=True)
show_smap = st.sidebar.checkbox("💧 Show Soil Moisture (SMAP)", value=False)
show_flood = st.sidebar.checkbox("🌊 Show Flood Anomaly", value=False)

# --- Helper: dynamic scaling ---
def dynamic_vis(image, band, geom, palette, scale=1000):
    """Compute dynamic min/max (5–95th percentile) for better visualization."""
    stats = image.select(band).reduceRegion(
        reducer=ee.Reducer.percentile([5, 95]),
        geometry=geom,
        scale=scale,
        maxPixels=1e9
    ).getInfo()

    if not stats:
        return {"min": 0, "max": 1, "palette": palette}

    values = list(stats.values())
    band_min, band_max = values[0], values[1]
    if band_min == band_max:
        band_min, band_max = 0, 1

    return {"min": band_min, "max": band_max, "palette": palette}

# --- NDVI Vegetation ---
if show_ndvi:
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")
    ndvi = (
        ee.ImageCollection("MODIS/061/MOD13Q1")
        .filterDate(start, end)
        .select("NDVI")
        .mean()
        .clip(sindh_geom)
    )
    ndvi_vis = dynamic_vis(ndvi, "NDVI", sindh_geom, ["brown", "yellow", "green"], scale=500)
    ndvi_layer = ndvi.visualize(**ndvi_vis)

    folium.TileLayer(
        tiles=ndvi_layer.getMapId()["tile_fetcher"].url_format,
        name="🌱 NDVI Vegetation",
        attr="MODIS NDVI",
        overlay=True,
        control=True,
        opacity=0.8
    ).add_to(m)

# --- Soil Moisture (ERA5-Land) Layer ---
if show_smap:
    def get_era5_soilmoisture(year, month, _geom):
        """Returns mean ERA5-Land volumetric soil water for top layer (0–7 cm) in the given month."""
        start = ee.Date.fromYMD(year, month, 1)
        end = start.advance(1, "month")

        sm = (
            ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY")
            .filterDate(start, end)
            .select("volumetric_soil_water_layer_1")  # Top 0–7 cm
            .mean()
            .clip(_geom)
        )
        return sm

    sm_layer = get_era5_soilmoisture(year, month, sindh_geom)

    vis_params = {
        "min": 0.05,  # drier soil
        "max": 0.45,  # saturated soil
        "palette": ["brown", "yellow", "green", "blue"]
    }

    ee_layer = sm_layer.visualize(**vis_params)
    layer_name = "Soil Moisture (ERA5, 0–7 cm)"

    folium.TileLayer(
        tiles=ee_layer.getMapId()["tile_fetcher"].url_format,
        name="💧 Soil Moisture",
        attr="NASA SMAP",
        overlay=True,
        control=True,
        opacity=0.8
    ).add_to(m)

# --- Flood Anomaly ---
if show_flood:
    dataset = ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR").select("total_precipitation_sum")
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")

    this_month = dataset.filterDate(start, end).mean()
    baseline = dataset.filterDate("2001-01-01", "2020-12-31").mean()
    anomaly = this_month.subtract(baseline).clip(sindh_geom)

    flood_vis = dynamic_vis(anomaly, "total_precipitation_sum", sindh_geom,
                            ["blue", "white", "red"], scale=10000)
    flood_layer = anomaly.visualize(**flood_vis)

    folium.TileLayer(
        tiles=flood_layer.getMapId()["tile_fetcher"].url_format,
        name="🌊 Flood Anomaly",
        attr="ECMWF ERA5",
        overlay=True,
        control=True,
        opacity=0.8
    ).add_to(m)

# -----------------------------
# 8d. Indus River
# -----------------------------
if river_gdf is not None:
    folium.GeoJson(
        river_gdf,
        name="Indus River",
        style_function=lambda x: {"color": "blue", "weight": 2, "opacity": 0.8},
        tooltip="Indus River"
    ).add_to(m)

# -----------------------------
# 9. District Polygons + Popups + Forecast Data
# -----------------------------
charts_data = []

for idx, row in sindh_gdf.iterrows():
    district_name = row.get("NAME_2", f"District-{idx}")
    geom = ee.Geometry(row["geometry"].__geo_interface__)

    # --- NDVI value ---
    try:
        ndvi_val = (
            ee.ImageCollection("MODIS/061/MOD13Q1")
            .filterDate(f"{year}-{month:02d}-01", f"{year}-{month:02d}-28")
            .select("NDVI")
            .mean()
            .reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=500,
                maxPixels=1e9
            )
            .get("NDVI")
            .getInfo()
        )
    except:
        ndvi_val = None

    # --- Popup text ---
    popup_text = f"<b>{district_name}</b><br>"
    if ndvi_val:
        popup_text += f"🟢 Avg NDVI ({year}-{month}): {ndvi_val/10000:.2f}<br>"

    if district_name in FAO_YIELD.get(selected_crop, {}):
        popup_text += f"🌾 {selected_crop} Yield: {FAO_YIELD[selected_crop][district_name]} t/ha<br>"

    # --- Forecast (from locations dictionary) ---
    if district_name in locations:
        lat, lon = locations[district_name]
        forecast = fetch_forecast(lat, lon)
        if forecast and "daily" in forecast:
            fdata = forecast["daily"]
            temps = fdata.get("temperature_2m_max", [])
            rains = fdata.get("precipitation_sum", [])
            if temps and rains:
                popup_text += f"🌡 Avg Temp: {np.mean(temps):.1f} °C<br>"
                popup_text += f"🌧 Rain (7d): {np.sum(rains):.1f} mm<br>"
            charts_data.append({
                "city": district_name,
                "dates": fdata["time"],
                "temp_max": temps,
                "temp_min": fdata.get("temperature_2m_min", []),
                "rain": rains
            })

    # --- Add polygon to map ---
    folium.GeoJson(
        data={"type": "Feature", "geometry": row["geometry"].__geo_interface__},
        name=district_name,
        style_function=lambda x: {"fillColor": "transparent", "color": "black", "weight": 1},
        tooltip=popup_text
    ).add_to(m)

# -----------------------------
# Popup Settings (handled in district loop below)
# -----------------------------
# (popup text is now built dynamically inside the district loop)

# -----------------------------
# Add Legend for Overlays
# -----------------------------
def add_legend(map_object, overlay_choice):
    base_style = """
        position: fixed; 
        bottom: 80px; left: 5px; 
        z-index:9999; 
        font-size:14px; 
        background-color: rgba(255,255,255,0.92);
        border:2px solid #444;
        padding: 10px;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.4);
        color: #111;
        font-weight: 600;
    """

    if overlay_choice == "NDVI Vegetation":
        legend_html = f"""
         <div style="{base_style} width:190px; height:130px;">
         <b>🌱 NDVI</b><br>
         <i style="background:brown;width:18px;height:18px;float:left;margin-right:6px"></i> Low (0.0)<br>
         <i style="background:yellow;width:18px;height:18px;float:left;margin-right:6px"></i> Medium (0.5)<br>
         <i style="background:green;width:18px;height:18px;float:left;margin-right:6px"></i> High (0.9+)<br>
         </div>
        """

    elif overlay_choice == "Soil Moisture (SMAP)":
        legend_html = f"""
         <div style="{base_style} width:210px; height:160px;">
         <b>💧 Soil Moisture</b><br>
         <i style="background:brown;width:18px;height:18px;float:left;margin-right:6px"></i> Dry (0.05)<br>
         <i style="background:yellow;width:18px;height:18px;float:left;margin-right:6px"></i> Moderate (0.2)<br>
         <i style="background:lightgreen;width:18px;height:18px;float:left;margin-right:6px"></i> Moist (0.3)<br>
         <i style="background:blue;width:18px;height:18px;float:left;margin-right:6px"></i> Saturated (0.45)<br>
         </div>
        """

    elif overlay_choice == "Flood Anomaly":
        legend_html = f"""
         <div style="{base_style} width:210px; height:160px;">
         <b>🌊 Flood Anomaly</b><br>
         <i style="background:blue;width:18px;height:18px;float:left;margin-right:6px"></i> Wet (Excess Rain)<br>
         <i style="background:white;width:18px;height:18px;float:left;margin-right:6px;border:1px solid black"></i> Normal<br>
         <i style="background:red;width:18px;height:18px;float:left;margin-right:6px"></i> Dry (Deficit)<br>
         </div>
        """

    map_object.get_root().html.add_child(folium.Element(legend_html))

# Call it here, after adding the overlay
if show_ndvi:
    overlay_choice = "NDVI Vegetation"
elif show_smap:
    overlay_choice = "Soil Moisture (SMAP)"
elif show_flood:
    overlay_choice = "Flood Anomaly"
else:
    overlay_choice = "NDVI Vegetation"  # default

add_legend(m, overlay_choice)

# -----------------------------
# 10. Show Map
# -----------------------------
st_map = st_folium(m, width=850, height=600)

# -----------------------------
# 11. Forecast Charts
# -----------------------------
# Prepare charts_data by fetching weather forecast for each district
charts_data = []
for city, (lat, lon) in locations.items():
    forecast = fetch_forecast(lat, lon)
    if "daily" in forecast:
        daily = forecast["daily"]
        charts_data.append({
            "city": city,
            "dates": daily.get("time", []),
            "temp_max": daily.get("temperature_2m_max", []),
            "temp_min": daily.get("temperature_2m_min", []),
            "rain": daily.get("precipitation_sum", [])
        })

if charts_data:
    st.subheader("📊 Forecast Charts (7-Day)")
    selected_city = st.selectbox("Select District for Chart", [d["city"] for d in charts_data])
    city_data = next(d for d in charts_data if d["city"] == selected_city)

    df_chart = pd.DataFrame({
        "Date": city_data["dates"],
        "Temp Max (°C)": city_data["temp_max"],
        "Temp Min (°C)": city_data["temp_min"],
        "Rain (mm)": city_data["rain"]
    }).dropna()

    fig = px.line(df_chart, x="Date", y=["Temp Max (°C)", "Temp Min (°C)", "Rain (mm)"],
                  markers=True, title=f"7-Day Forecast for {selected_city}")
    st.plotly_chart(fig, use_container_width=True)
# -----------------------------
# 12. Irrigation Advisory
# -----------------------------
st.subheader("💧 Irrigation Advisory")

# Simplified crop water requirement factors (mm/week)
CROP_WATER_REQUIREMENT = {
    "Wheat": 35,
    "Rice": 50,
    "Cotton": 40,
    "Sugarcane": 55
}

if charts_data and selected_crop:
    selected_city = st.selectbox("Select District for Advisory", [d["city"] for d in charts_data], key="advisory_city")
    city_data = next(d for d in charts_data if d["city"] == selected_city)

    df_weather = pd.DataFrame({
        "Date": city_data["dates"],
        "Temp Max (°C)": city_data["temp_max"],
        "Temp Min (°C)": city_data["temp_min"],
        "Rain (mm)": city_data["rain"]
    }).dropna()

    # Calculate weekly averages
    avg_temp = df_weather["Temp Max (°C)"].mean()
    total_rain = df_weather["Rain (mm)"].sum()

    crop_need = CROP_WATER_REQUIREMENT[selected_crop]

    if total_rain < crop_need:
        st.error(
            f"🚰 Irrigation Required in **{selected_city}** for {selected_crop}. "
            f"Weekly Rainfall = {total_rain:.1f} mm, Crop Need = {crop_need} mm."
        )
    else:
        st.success(
            f"✅ No irrigation needed in **{selected_city}** for {selected_crop}. "
            f"Weekly Rainfall = {total_rain:.1f} mm, Crop Need = {crop_need} mm."
        )

# -----------------------------
# 13. Flood Risk Advisory
# -----------------------------
st.subheader("🌊 Flood Risk Advisory")

if charts_data:
    selected_city_flood = st.selectbox("Select District for Flood Risk Check", 
                                       [d["city"] for d in charts_data], key="flood_city")
    city_data_flood = next(d for d in charts_data if d["city"] == selected_city_flood)

    df_flood = pd.DataFrame({
        "Date": city_data_flood["dates"],
        "Rain (mm)": city_data_flood["rain"]
    }).dropna()

    total_rain = df_flood["Rain (mm)"].sum()

    # Threshold for flood risk (you can tune this value)
    FLOOD_THRESHOLD = 70  # mm in 7 days

    if total_rain > FLOOD_THRESHOLD:
        st.error(
            f"⚠️ High Flood Risk in **{selected_city_flood}**. "
            f"7-day Rainfall = {total_rain:.1f} mm (Threshold = {FLOOD_THRESHOLD} mm). "
            f"Stay alert for possible waterlogging or flooding."
        )
    else:
        st.success(
            f"✅ Low Flood Risk in **{selected_city_flood}**. "
            f"7-day Rainfall = {total_rain:.1f} mm."
        )

# -----------------------------
# FAO Yield Chart
# -----------------------------
if selected_crop:
    st.subheader(f"🌾 FAO Crop Yield Data for {selected_crop}")
    crop_dict = FAO_YIELD.get(selected_crop, {})
    if crop_dict:
        df_crop = pd.DataFrame(list(crop_dict.items()), columns=["District", "Yield (t/ha)"])
        fig2 = px.bar(df_crop, x="District", y="Yield (t/ha)",
                      color="Yield (t/ha)",
                      title=f"{selected_crop} Yield by District")
        st.plotly_chart(fig2, use_container_width=True)

# -----------------------------
#  NDVI Growth Trend (12 months)
# -----------------------------
st.subheader(f"🌱 NDVI Growth Trend - {selected_crop}")

if selected_crop:
    ndvi_trends = []
    today = ee.Date(datetime.date.today().strftime("%Y-%m-%d"))
    one_year_ago = today.advance(-1, "year")

    for district, yield_val in FAO_YIELD.get(selected_crop, {}).items():
        row = sindh_gdf[sindh_gdf["NAME_2"] == district]
        if row.empty:
            continue
        geom = ee.Geometry(row.iloc[0]["geometry"].__geo_interface__)

        dataset = (
            ee.ImageCollection("MODIS/061/MOD13Q1")
            .filterDate(one_year_ago, today)
            .select("NDVI")
        )

        def extract_ndvi(img):
            mean_dict = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=500,
                maxPixels=1e9
            )
            return ee.Feature(
                None,
                {
                    "date": img.date().format("YYYY-MM-dd"),
                    "NDVI": mean_dict.get("NDVI")
                }
            )

        ndvi_fc = dataset.map(extract_ndvi)
        ndvi_data = ndvi_fc.getInfo()

        dates, values = [], []
        for f in ndvi_data["features"]:
            if f["properties"]["NDVI"] is not None:
                dates.append(f["properties"]["date"])
                values.append(f["properties"]["NDVI"] / 10000)

        if dates:
            df = pd.DataFrame({"Date": pd.to_datetime(dates), "NDVI": values})
            df = df.sort_values("Date")

            # Apply rolling mean smoothing (3 periods)
            df["NDVI_Smoothed"] = df["NDVI"].rolling(window=3, min_periods=1).mean()

            # Normalize NDVI between 0–1 for better comparison
            df["NDVI_Normalized"] = (df["NDVI_Smoothed"] - df["NDVI_Smoothed"].min()) / (
                df["NDVI_Smoothed"].max() - df["NDVI_Smoothed"].min()
            )

            ndvi_trends.append({"district": district, "df": df})

    if ndvi_trends:
        for ndvi in ndvi_trends:
            df_ndvi = ndvi["df"]

            fig_ndvi = px.area(
                df_ndvi, x="Date", y="NDVI_Normalized",
                title=f"NDVI Growth Trend (Normalized) - {ndvi['district']} ({selected_crop})",
                labels={"NDVI_Normalized": "Normalized NDVI (0–1)"}
            )
            fig_ndvi.update_traces(line_color="green", fill="tozeroy")
            st.plotly_chart(fig_ndvi, use_container_width=True)
