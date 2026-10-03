
import streamlit as st

# Configure the browser tab and page layout.
st.set_page_config(
    page_title="Satellite Crop Monitor",
    page_icon="🌱",
    layout="wide",
)

# Display the application heading.
st.title("Satellite-Based Crop Health Monitor")

# Explain the purpose of the application.
st.write(
    "Monitor vegetation using satellite imagery "
    "and the Normalized Difference Vegetation Index (NDVI)."
)

# Temporary message until satellite data is connected.
st.info(
    "Project setup is complete. Satellite data "
    "integration will be added in the next stages."
)
