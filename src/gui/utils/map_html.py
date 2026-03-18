from __future__ import annotations

import json
from string import Template
from pathlib import Path

from utils.resources import require_resource


def render_map_html(title: str, src_points: list[dict], tgt_points: list[dict]) -> tuple[str, str]:
    """
    Возвращает:
      html_text, base_url
    base_url нужен WebView для разрешения относительных путей ../maplibre/*
    """
    tpl = require_resource("web/templates/map_dialog.html.tpl").read_text(encoding="utf-8")
    js  = require_resource("web/maplibre/maplibre-gl.js").read_text(encoding="utf-8")
    css = require_resource("web/maplibre/maplibre-gl.css").read_text(encoding="utf-8")
    geojs = require_resource("web/lib/geographiclib-geodesic.min.js").read_text(encoding="utf-8")

    html = (
        tpl.replace("__MAPLIBRE_JS__", js)
        .replace("__MAPLIBRE_CSS__", css)
        .replace("__GEOGRAPHICLIB_JS__", geojs)
        .replace("__SRC_POINTS_JSON__", json.dumps(src_points, ensure_ascii=False))
        .replace("__TGT_POINTS_JSON__", json.dumps(tgt_points, ensure_ascii=False))
        .replace("__MAP_TITLE__", json.dumps(title, ensure_ascii=False))
    )
    return html