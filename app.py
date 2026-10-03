
import streamlit as st
import ee
import folium
import pandas as pd

from datetime import date, timedelta
from streamlit_folium import st_folium

from src.satellite import (
    STUDY_AREAS,
    initialize_earth_engine,
    get_sentinel2_ndvi,
    get_mean_ndvi,
    get_ndvi_map_tiles,
    get_monthly_ndvi_trend,
)


st.set_page_config(
    page_title="Satellite Crop Monitor",
    page_icon="🌱",
    layout="wide",
)

st.title("🌱 Satellite-Based Crop Health Monitor")
st.write(
    "Explore vegetation conditions using Sentinel-2 "
    "satellite imagery and NDVI."
)

# Sidebar controls
st.sidebar.header("Analysis Settings")

location = st.sidebar.selectbox(
    "Study area",
    options=list(STUDY_AREAS.keys()),
)

start_date = st.sidebar.date_input(
    "Start date",
    value=date(2025, 1, 1),
    min_value=date(2017, 3, 28),
    max_value=date.today(),
)

end_date = st.sidebar.date_input(
    "End date",
    value=date(2025, 12, 31),
    min_value=date(2017, 3, 28),
    max_value=date.today(),
)

max_cloud = st.sidebar.slider(
    "Maximum cloud cover (%)",
    min_value=0,
    max_value=100,
    value=20,
    step=5,
)

st.sidebar.caption(
    "Satellite data: Sentinel-2 Surface Reflectance"
)

if start_date > end_date:
    st.error("Start date must be on or before end date.")
    st.stop()

try:
    with st.spinner("Connecting to Earth Engine..."):
        initialize_earth_engine()

    with st.spinner("Processing satellite imagery..."):
        ndvi, study_area, image_count = get_sentinel2_ndvi(
            location=location,
            start_date=start_date,
            end_date=end_date,
            max_cloud=max_cloud,
        )

        count = image_count.getInfo()

    if count == 0:
        st.warning(
            "No satellite images matched these filters. "
            "Try a longer date range or a higher cloud-cover limit."
        )
        st.stop()

    mean_ndvi = get_mean_ndvi(ndvi, study_area)

    # Display metrics
    col1, col2, col3 = st.columns(3)

    col1.metric("Matching satellite images", count)

    col2.metric(
        "Mean NDVI",
        f"{mean_ndvi:.3f}"
        if mean_ndvi is not None
        else "N/A",
    )

    col3.metric("Maximum cloud cover", f"{max_cloud}%")

    st.caption(
        f"Study area: {location} | "
        f"Period: {start_date} to {end_date}"
    )

    # Create the interactive map
    map_data = get_ndvi_map_tiles(ndvi)

    west, south, east, north = STUDY_AREAS[location]
    center_lat = (south + north) / 2
    center_lon = (west + east) / 2

    crop_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles="OpenStreetMap",
    )

    folium.TileLayer(
        tiles=map_data["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name="NDVI",
        overlay=True,
        control=True,
    ).add_to(crop_map)

    folium.LayerControl().add_to(crop_map)

    st.subheader("NDVI Map")
    st_folium(
        crop_map,
        width=None,
        height=550,
        key="ndvi_map",
    )

    # NDVI legend
    st.subheader("Understanding the NDVI map")

    legend_cols = st.columns(4)

    legend_items = [
        ("Brown", "Low or negative NDVI"),
        ("Yellow", "Low vegetation greenness"),
        ("Light green", "Moderate vegetation greenness"),
        ("Dark green", "Higher vegetation greenness"),
    ]

    for col, (color, description) in zip(
        legend_cols, legend_items
    ):
        col.markdown(f"**{color}**")
        col.caption(description)

    st.caption(
        "NDVI indicates vegetation greenness. Values can also "
        "be affected by soil, crop type, growth stage and season. "
        "It is not a definitive diagnosis of crop health."
    )



    # Monthly NDVI trend chart
    st.subheader("Monthly Vegetation Trend")

    with st.spinner("Calculating monthly NDVI trends..."):
        monthly_results = get_monthly_ndvi_trend(
            location=location,
            start_date=start_date,
            end_date=end_date,
            max_cloud=max_cloud,
        )

    if monthly_results:
        trend_df = pd.DataFrame(monthly_results)

        # Convert missing values to proper chart gaps.
        trend_df["Mean NDVI"] = pd.to_numeric(
            trend_df["Mean NDVI"],
            errors="coerce",
        )

        trend_df["Month"] = pd.to_datetime(
            trend_df["Month"],
            format="%Y-%m",
        )

        trend_df = trend_df.set_index("Month")

        st.line_chart(
            trend_df[["Mean NDVI"]],
            y="Mean NDVI",
            x_label="Month",
            y_label="Mean NDVI",
        )

        with st.expander("View monthly data"):
            st.dataframe(
                trend_df,
                use_container_width=True,
            )
    else:
        st.info("No monthly trend data is available.")


except Exception as error:
    st.error("Unable to load satellite data.")
    st.exception(error)
