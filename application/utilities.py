#!/usr/bin/env python3


import numpy as np
from lxml import etree


def export_to_gpx(coordinates: np.ndarray, filename: str) -> None:
    """
    Export a NumPy array of coordinates to a GPX file.

    :param np.ndarray coordinates: An array of coordinates with shape (n, 2) or (n, 3). Each
    coordinate should be in the form [latitude, longitude] or [latitude, longitude, elevation].
    :param str filename: The name of the output GPX file.
    :return None:
    """
    # Create the root element
    gpx = etree.Element("gpx", version="1.1", creator="export_to_gpx_function")
    trk = etree.SubElement(gpx, "trk")
    trkseg = etree.SubElement(trk, "trkseg")
    # Add coordinates to the GPX file
    for coord in coordinates:
        trkpt = etree.SubElement(trkseg, "trkpt", lat=str(coord[0]), lon=str(coord[1]))
        if len(coord) == 3:
            ele = etree.SubElement(trkpt, "ele")
            ele.text = str(coord[2])
    # Create a tree and write to a file
    tree = etree.ElementTree(gpx)
    tree.write(filename, pretty_print=True, xml_declaration=True, encoding="UTF-8")
