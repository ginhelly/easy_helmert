from __future__ import annotations

from typing import List, Dict, Tuple
from xml.sax.saxutils import escape


def _hull(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Monotonic chain convex hull, вход: [(lon, lat), ...]."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return []

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull = lower[:-1] + upper[:-1]
    return hull


def _placemark_point(name: str, lon: float, lat: float) -> str:
    return (
        "<Placemark>"
        f"<name>{escape(name)}</name>"
        "<Point>"
        f"<coordinates>{lon:.10f},{lat:.10f},0</coordinates>"
        "</Point>"
        "</Placemark>"
    )


def build_kml(
    src_points: List[Dict],
    tgt_points: List[Dict],
    doc_name: str = "Точки калибровки",
) -> str:
    src_pm = []
    for p in src_points:
        try:
            src_pm.append(
                "<Placemark>"
                f"<name>{escape(p.get('name', 'src'))}</name>"
                "<styleUrl>#srcPointStyle</styleUrl>"
                "<Point>"
                f"<coordinates>{float(p['lon']):.10f},{float(p['lat']):.10f},0</coordinates>"
                "</Point>"
                "</Placemark>"
            )
        except Exception:
            pass

    tgt_pm = []
    tgt_coords = []
    for p in tgt_points:
        try:
            lon = float(p["lon"])
            lat = float(p["lat"])
            tgt_pm.append(
                "<Placemark>"
                f"<name>{escape(p.get('name', 'tgt'))}</name>"
                "<styleUrl>#tgtPointStyle</styleUrl>"
                "<Point>"
                f"<coordinates>{lon:.10f},{lat:.10f},0</coordinates>"
                "</Point>"
                "</Placemark>"
            )
            tgt_coords.append((lon, lat))
        except Exception:
            pass

    hull = _hull(tgt_coords)
    hull_pm = ""
    if len(hull) >= 3:
        ring = hull + [hull[0]]
        coord_str = " ".join(f"{lon:.10f},{lat:.10f},0" for lon, lat in ring)
        hull_pm = (
            "<Placemark>"
            "<name>Convex Hull</name>"
            "<styleUrl>#hullPolyStyle</styleUrl>"
            "<Polygon><outerBoundaryIs><LinearRing>"
            f"<coordinates>{coord_str}</coordinates>"
            "</LinearRing></outerBoundaryIs></Polygon>"
            "</Placemark>"
        )

    # KML цвет = aabbggrr (не rgb!)
    # src #1565C0 -> c06515
    # tgt #C62828 -> 2828C6
    # hull #f4633a -> 3a63f4
    #
    # Полигон: fill opacity \~15% => alpha \~26 (hex 1A)
    # Линия hull: alpha 255 (FF)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{escape(doc_name)}</name>

    <Style id="srcPointStyle">
      <IconStyle>
        <color>ffc06515</color>
        <scale>0.9</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>
        </Icon>
      </IconStyle>
      <LabelStyle>
        <color>ffb04d0d</color>
        <scale>0.95</scale>
      </LabelStyle>
    </Style>

    <Style id="tgtPointStyle">
      <IconStyle>
        <color>ff2828c6</color>
        <scale>0.9</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>
        </Icon>
      </IconStyle>
      <LabelStyle>
        <color>ff00008e</color>
        <scale>0.95</scale>
      </LabelStyle>
    </Style>

    <Style id="hullPolyStyle">
      <LineStyle>
        <color>ff3a63f4</color>
        <width>2</width>
      </LineStyle>
      <PolyStyle>
        <color>1a3a63f4</color>
        <fill>1</fill>
        <outline>1</outline>
      </PolyStyle>
    </Style>

    <Folder>
      <name>Исходные точки</name>
      {''.join(src_pm)}
    </Folder>

    <Folder>
      <name>Опорные точки</name>
      {''.join(tgt_pm)}
    </Folder>

    <Folder>
      <name>Территория калибровки</name>
      {hull_pm}
    </Folder>

  </Document>
</kml>
"""