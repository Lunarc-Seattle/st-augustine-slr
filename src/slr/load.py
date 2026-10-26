"""Read the source files and clip them to the city in a metric CRS.

Everything leaves this module in ``area_crs`` (EPSG:26917) so that areas are
in square metres and every later step can trust the units.
"""

import geopandas as gpd

# TIGER/Line and the NOAA vectors are both stored in NAD83 geographic coordinates.
SOURCE_CRS = "EPSG:4269"


def load_city(places_zip, name, statefp, crs):
    """Return the one city polygon; fail loudly if the name is ambiguous."""
    places = gpd.read_file(places_zip)
    city = places[(places["NAME"] == name) & (places["STATEFP"] == statefp)]
    if len(city) != 1:
        raise ValueError(f"Expected 1 place named {name!r}, found {len(city)}")
    return city[["GEOID", "NAME", "geometry"]].to_crs(crs).reset_index(drop=True)


def read_clipped(path, city, layer=None):
    """Read only features near the city (bbox filter), then clip to its outline.

    The bbox filter is what keeps the 1.1 GB NOAA geopackage cheap to read.
    """
    bbox = tuple(city.to_crs(SOURCE_CRS).total_bounds)
    gdf = gpd.read_file(path, layer=layer, bbox=bbox)
    return gpd.clip(gdf.to_crs(city.crs), city)


def land_polygon(city, water):
    """Census land = city outline minus Census water bodies.

    NOAA's inundation polygons include rivers and bays that are water today,
    so they must be intersected with land before we call anything "land loss".
    """
    return city.geometry.iloc[0].difference(water.union_all())


def noaa_gpkg_path(zip_path, member):
    """GDAL path that reads the geopackage straight out of the zip."""
    return f"/vsizip/{zip_path}/{member}"


def noaa_layer(prefix, kind, level_ft):
    """Layer name for a kind ('slr' or 'low') and level, e.g. FL_NE_slr_3_0ft."""
    whole, half = divmod(round(level_ft * 10), 10)
    return f"{prefix}_{kind}_{whole}_{half}ft"
