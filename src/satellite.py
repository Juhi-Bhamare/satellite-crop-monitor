

import calendar
from datetime import date
import ee
from datetime import date, timedelta



# Preset study areas: (west, south, east, north)

STUDY_AREAS = {
    "Mumbai, Maharashtra": [
        72.8277, 19.0260, 72.9277, 19.1260
    ],
    "Pune, Maharashtra": [
        73.8067, 18.4704, 73.9067, 18.5704
    ],
    "Solapur, Maharashtra": [
        75.8564, 17.6099, 75.9564, 17.7099
    ],
    "Nashik, Maharashtra": [
        73.7398, 19.9475, 73.8398, 20.0475
    ],
    "Nagpur, Maharashtra": [
        79.0382, 21.0958, 79.1382, 21.1958
    ],
    "Kolhapur, Maharashtra": [
        74.1933, 16.6550, 74.2933, 16.7550
    ],
    "Chhatrapati Sambhajinagar, Maharashtra": [
        75.2933, 19.8262, 75.3933, 19.9262
    ],
    "Hyderabad, Telangana": [
        78.4367, 17.3350, 78.5367, 17.4350
    ],
    "Bengaluru, Karnataka": [
        77.5446, 12.9216, 77.6446, 13.0216
    ],
    "Indore, Madhya Pradesh": [
        75.8077, 22.6696, 75.9077, 22.7696
    ],
    "Jaipur, Rajasthan": [
        75.7373, 26.8624, 75.8373, 26.9624
    ],
    "Ahmedabad, Gujarat": [
        72.5214, 22.9725, 72.6214, 23.0725
    ],
    "Chennai, Tamil Nadu": [
        80.2207, 13.0327, 80.3207, 13.1327
    ],
    "Delhi": [
        77.1590, 28.5639, 77.2590, 28.6639
    ],
}



def initialize_earth_engine():
    """Connect Python to Google Earth Engine."""
    ee.Initialize(project="satellite-crop-monitor")


def get_sentinel2_ndvi(
    location="Solapur, Maharashtra",
    start_date=date(2025, 1, 1),
    end_date=date(2025, 12, 31),
    max_cloud=20,
):
    """Retrieve Sentinel-2 imagery and calculate NDVI."""

    if location not in STUDY_AREAS:
        raise ValueError("Please select a supported study area.")

    if start_date > end_date:
        raise ValueError("Start date must be before end date.")

    # Define the selected study area.
    study_area = ee.Geometry.Rectangle(
        list(STUDY_AREAS[location])
    )

    # Earth Engine's end date is exclusive.
    exclusive_end = end_date + timedelta(days=1)

    # Load and filter Sentinel-2 surface reflectance imagery.
    images = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(study_area)
        .filterDate(
            start_date.isoformat(),
            exclusive_end.isoformat(),
        )
        .filter(
            ee.Filter.lte(
                "CLOUDY_PIXEL_PERCENTAGE",
                max_cloud,
            )
        )
    )

    # Count matching images before creating the composite.
    image_count = images.size()

    # Create the median composite and calculate NDVI.
    composite = images.median().clip(study_area)

    ndvi = composite.normalizedDifference(
        ["B8", "B4"]
    ).rename("NDVI")

    return ndvi, study_area, image_count


def get_mean_ndvi(ndvi, study_area):
    """Calculate mean NDVI across the study area."""

    mean_value = ndvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=study_area,
        scale=20,
        maxPixels=2_000_000,
        bestEffort=True,
    )

    return mean_value.get("NDVI").getInfo()


def get_ndvi_map_tiles(ndvi):
    """Create map tile information for the NDVI image."""

    visualization = {
        "min": -0.2,
        "max": 0.8,
        "palette": [
            "brown",
            "yellow",
            "lightgreen",
            "darkgreen",
        ],
    }

    return ndvi.getMapId(visualization)



def get_monthly_ndvi_trend(
    location,
    start_date,
    end_date,
    max_cloud=20,
):
    """Calculate monthly mean NDVI for a selected study area."""

    west, south, east, north = STUDY_AREAS[location]

    study_area = ee.Geometry.Rectangle([
        west, south, east, north
    ])

    start = date(
        start_date.year,
        start_date.month,
        1,
    )

    # Make the selected end date inclusive.
    end_exclusive = date.fromordinal(
        end_date.toordinal() + 1
    )

    months = []
    current = start

    while current < end_exclusive:
        if current.month == 12:
            next_month = date(current.year + 1, 1, 1)
        else:
            next_month = date(
                current.year,
                current.month + 1,
                1,
            )

        period_start = max(current, start_date)
        period_end = min(next_month, end_exclusive)

        images = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(study_area)
            .filterDate(
                period_start.isoformat(),
                period_end.isoformat(),
            )
            .filter(
                ee.Filter.lte(
                    "CLOUDY_PIXEL_PERCENTAGE",
                    max_cloud,
                )
            )
        )

        count = images.size()

        composite = images.median().clip(study_area)

        ndvi = composite.normalizedDifference(
            ["B8", "B4"]
        ).rename("NDVI")

        mean_value = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=study_area,
            scale=20,
            maxPixels=2_000_000,
            bestEffort=True,
        ).get("NDVI")

        # Keep months without imagery so the chart can
        # represent gaps instead of hiding them.
        feature = ee.Feature(None, {
            "month": current.strftime("%Y-%m"),
            "image_count": count,
            "mean_ndvi": ee.Algorithms.If(
                count.gt(0),
                mean_value,
                None,
            ),
        })

        months.append(feature)
        current = next_month

    result = ee.FeatureCollection(months).getInfo()

    return [
        {
            "Month": feature["properties"]["month"],
            "Mean NDVI": feature["properties"].get(
                "mean_ndvi"
            ),
            "Images": feature["properties"]["image_count"],
        }
        for feature in result["features"]
    ]
