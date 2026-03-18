<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="referrer" content="origin" />
  <title>__MAP_TITLE__</title>

  <style>
__MAPLIBRE_CSS__
  </style>

  <style>
    html, body, #map { margin:0; padding:0; width:100%; height:100%; font-family:Segoe UI, Arial, sans-serif; }

    .legend {
      position: absolute;
      left: 10px;
      bottom: 10px;   /* было top */
      z-index: 10;
      background: rgba(255,255,255,.95);
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 12px;
      line-height: 1.35;
      min-width: 220px;
    }
    .dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align:middle; }
    .src { background:#1565C0; }
    .tgt { background:#C62828; }

    .ctrl {
      position: absolute;
      left: 10px;     /* было right */
      top: 10px;
      z-index: 10;
      background: rgba(255,255,255,.95);
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 12px;
    }

    .error-box {
      margin:14px; padding:12px; border:1px solid #e57373; border-radius:8px;
      background:#ffebee; color:#7f0000; font-size:13px; white-space:pre-wrap;
    }

    .small { color:#666; font-size:11px; margin-top:6px; }

    #rulerInfo {
      display: none;
      margin-top: 8px;
      font-size: 14px;
      font-weight: 700;
      color: #111;
      line-height: 1.3;
    }
  </style>
</head>
<body>
  <div id="map"></div>

  <div class="legend">
    <div><strong id="legend-title"></strong></div>
    <div><span class="dot src"></span>Исходные точки</div>
    <div><span class="dot tgt"></span>Опорные точки</div>
    <div><span class="dot" style="background:#f4633a;"></span>Территория калибровки</div>
    <div class="small" id="attribution-extra"></div>
  </div>

  <div class="ctrl">
    <label for="basemapSelect"><strong>Подложка:</strong></label><br/>
    <select id="basemapSelect">
      <option value="google_hybrid">Google Satellite Hybrid</option>
      <option value="osm">OSM Standard</option>
      <option value="esri_imagery">Esri World Imagery</option>
      <option value="carto_light">Carto Light</option>
    </select>
    <div style="margin-top:8px;">
      <button id="btnRulerToggle" type="button">Линейка: выкл</button>
      <button id="btnRulerClear" type="button">Очистить</button>
    </div>
    <div id="rulerInfo" class="small">Расстояние: —</div>
  </div>

  <script>
__MAPLIBRE_JS__
  </script>

  <script>
__GEOGRAPHICLIB_JS__
  </script>

  <script>
  (function () {
    function showError(msg) {
      console.error(msg);
      const mapEl = document.getElementById("map");
      if (mapEl) {
        mapEl.innerHTML = '<div class="error-box">' + String(msg) + "</div>";
      }
    }

    function asFeature(p) {
      return {
        type: "Feature",
        geometry: { type: "Point", coordinates: [Number(p.lon), Number(p.lat)] },
        properties: { name: p.name || "" }
      };
    }

    function cross(o, a, b) {
      return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    }

    function convexHull(points) {
      if (!points || points.length < 3) return null;

      const uniq = [];
      const seen = new Set();
      for (const p of points) {
        const k = p[0].toFixed(12) + "|" + p[1].toFixed(12);
        if (!seen.has(k)) {
          seen.add(k);
          uniq.push(p);
        }
      }
      if (uniq.length < 3) return null;

      uniq.sort((p1, p2) => (p1[0] === p2[0] ? p1[1] - p2[1] : p1[0] - p2[0]));

      const lower = [];
      for (const p of uniq) {
        while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) {
          lower.pop();
        }
        lower.push(p);
      }

      const upper = [];
      for (let i = uniq.length - 1; i >= 0; i--) {
        const p = uniq[i];
        while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) {
          upper.pop();
        }
        upper.push(p);
      }

      lower.pop();
      upper.pop();
      const hull = lower.concat(upper);
      if (hull.length < 3) return null;
      hull.push(hull[0]);
      return hull;
    }

    // ===== ДАННЫЕ ИЗ PYTHON =====
    const SRC = __SRC_POINTS_JSON__;
    const TGT = __TGT_POINTS_JSON__;
    const MAP_TITLE = __MAP_TITLE__;

    const titleEl = document.getElementById("legend-title");
    if (titleEl) titleEl.textContent = MAP_TITLE;

    if (typeof maplibregl === "undefined" || typeof maplibregl.Map !== "function") {
      showError("MapLibre не загружен: maplibregl.Map недоступен");
      return;
    }

    // GeographicLib для эллипсоидной линейки (если подключён)
    const geod = (() => {
      // Вариант 1: твой файл экспортирует window.geodesic
      if (typeof geodesic !== "undefined" && geodesic.Geodesic && geodesic.Geodesic.WGS84) {
        return geodesic.Geodesic.WGS84;
      }
      // Вариант 2: другие сборки GeographicLib
      if (typeof GeographicLib !== "undefined" && GeographicLib.Geodesic && GeographicLib.Geodesic.WGS84) {
        return GeographicLib.Geodesic.WGS84;
      }
      return null;
    })();

    const srcFC = { type: "FeatureCollection", features: (SRC || []).map(asFeature) };
    const tgtFC = { type: "FeatureCollection", features: (TGT || []).map(asFeature) };

    const tgtCoords = (TGT || [])
      .map(p => [Number(p.lon), Number(p.lat)])
      .filter(c => Number.isFinite(c[0]) && Number.isFinite(c[1]));
    const hullCoords = convexHull(tgtCoords);

    // Подложки
    const basemaps = {
      osm: {
        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
        attribution: "© OpenStreetMap contributors"
      },
      google_hybrid: {
        tiles: ["https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"],
        attribution: "© Google"
      },
      esri_imagery: {
        tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
        attribution: "Source: Esri, Maxar, Earthstar Geographics and the GIS User Community"
      },
      carto_light: {
        tiles: [
          "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
          "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
          "https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
        ],
        attribution: "© OpenStreetMap contributors © CARTO"
      }
    };

    const styleSources = {
      src: { type: "geojson", data: srcFC },
      tgt: { type: "geojson", data: tgtFC },
      hull: {
        type: "geojson",
        data: hullCoords
          ? {
              type: "FeatureCollection",
              features: [{
                type: "Feature",
                geometry: { type: "Polygon", coordinates: [hullCoords] },
                properties: {}
              }]
            }
          : { type: "FeatureCollection", features: [] }
      }
    };

    for (const [id, bm] of Object.entries(basemaps)) {
      styleSources["bm_" + id] = {
        type: "raster",
        tiles: bm.tiles,
        tileSize: 256,
        attribution: bm.attribution
      };
    }

    const styleLayers = [];

    // basemaps
    for (const id of Object.keys(basemaps)) {
      styleLayers.push({
        id: "basemap_" + id,
        type: "raster",
        source: "bm_" + id,
        layout: { visibility: id === "google_hybrid" ? "visible" : "none" }
      });
    }

    // hull
    styleLayers.push(
      {
        id: "hull-fill",
        type: "fill",
        source: "hull",
        paint: {
          "fill-color": "#f4633a",
          "fill-opacity": 0.15
        }
      },
      {
        id: "hull-line",
        type: "line",
        source: "hull",
        paint: {
          "line-color": "#f4633a",
          "line-width": 2
        }
      }
    );

    // points + labels
    styleLayers.push(
      {
        id: "src-circles",
        type: "circle",
        source: "src",
        paint: {
          "circle-radius": 6,
          "circle-color": "#1565C0",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.5
        }
      },
      {
        id: "tgt-circles",
        type: "circle",
        source: "tgt",
        paint: {
          "circle-radius": 6,
          "circle-color": "#C62828",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.5
        }
      },
      {
        id: "src-labels",
        type: "symbol",
        source: "src",
        layout: {
          "text-field": ["get", "name"],
          "text-size": 13,
          "text-offset": [0, 1.15],
          "text-anchor": "top",
          "text-font": ["Open Sans Bold", "Noto Sans Bold"]
        },
        paint: {
          "text-color": "#0D47A1",
          "text-halo-color": "#FFFFFF",
          "text-halo-width": 1.8,
          "text-halo-blur": 0.4
        }
      },
      {
        id: "tgt-labels",
        type: "symbol",
        source: "tgt",
        layout: {
          "text-field": ["get", "name"],
          "text-size": 13,
          "text-offset": [0, 1.15],
          "text-anchor": "top",
          "text-font": ["Open Sans Bold", "Noto Sans Bold"]
        },
        paint: {
          "text-color": "#8E0000",
          "text-halo-color": "#FFFFFF",
          "text-halo-width": 1.8,
          "text-halo-blur": 0.4
        }
      }
    );

    const styleObj = { version: 8, sources: styleSources, layers: styleLayers };

    let map;
    try {
      map = new maplibregl.Map({
        container: "map",
        style: styleObj,
        center: [37.6176, 55.7558],
        zoom: 4
      });
    } catch (e) {
      showError("Не удалось создать карту:\n" + (e && e.message ? e.message : e));
      return;
    }

    try { map.addControl(new maplibregl.NavigationControl(), "top-right"); } catch (_) {}

    function setBasemap(id) {
      for (const k of Object.keys(basemaps)) {
        map.setLayoutProperty("basemap_" + k, "visibility", k === id ? "visible" : "none");
      }
      const a = basemaps[id] ? basemaps[id].attribution : "";
      const attrEl = document.getElementById("attribution-extra");
      if (attrEl) attrEl.textContent = a;
    }

    // ===== ЛИНЕЙКА =====
    let rulerOn = false;
    let rulerPts = []; // [[lon,lat], ...]

    const rulerInfo = document.getElementById("rulerInfo");
    const btnToggle = document.getElementById("btnRulerToggle");
    const btnClear = document.getElementById("btnRulerClear");

    function formatDist(m) {
      if (!Number.isFinite(m)) return "—";
      if (m < 1000) return `${m.toFixed(2)} м`;
      return `${(m / 1000).toFixed(3)} км`;
    }

    function calcEllipsoidLen(points) {
      if (!geod || points.length < 2) return 0.0;
      let s = 0.0;
      for (let i = 1; i < points.length; i++) {
        const p1 = points[i - 1];
        const p2 = points[i];
        const inv = geod.Inverse(p1[1], p1[0], p2[1], p2[0]); // lat1, lon1, lat2, lon2
        s += inv.s12;
      }
      return s;
    }

    function buildKilometerTickFeatures(points, geod) {
      // points: [[lon,lat], ...]
      if (!geod || points.length < 2) return [];

      const features = [];
      let acc = 0.0;          // пройдено, м
      let nextKm = 1000.0;    // следующая километровая метка
      const halfTick = 20.0;  // половина длины штриха (м), итоговая длина 40 м

      for (let i = 1; i < points.length; i++) {
        const p1 = points[i - 1];
        const p2 = points[i];

        const inv = geod.Inverse(p1[1], p1[0], p2[1], p2[0]); // lat1,lon1,lat2,lon2
        const segLen = inv.s12;
        const azi = inv.azi1;

        while (acc + segLen >= nextKm) {
          const sOnSeg = nextKm - acc;

          // точка на линии на расстоянии sOnSeg от начала сегмента
          const mid = geod.Direct(p1[1], p1[0], azi, sOnSeg);

          // короткий перпендикуляр к линии
          const left  = geod.Direct(mid.lat2, mid.lon2, azi - 90, halfTick);
          const right = geod.Direct(mid.lat2, mid.lon2, azi + 90, halfTick);

          features.push({
            type: "Feature",
            geometry: {
              type: "LineString",
              coordinates: [
                [left.lon2, left.lat2],
                [right.lon2, right.lat2]
              ]
            },
            properties: { km: Math.round(nextKm / 1000.0), kind: "tick" }
          });

          features.push({
            type: "Feature",
            geometry: {
              type: "Point",
              coordinates: [mid.lon2, mid.lat2]
            },
            properties: { km: Math.round(nextKm / 1000.0), kind: "label" }
          });

          nextKm += 1000.0;
        }

        acc += segLen;
      }

      return features;
    }

    function refreshRulerLayer() {
      const src = map.getSource("ruler");
      const srcTicks = map.getSource("ruler_ticks");
      if (!src || !srcTicks) return;

      const feats = [];

      for (const p of rulerPts) {
        feats.push({
          type: "Feature",
          geometry: { type: "Point", coordinates: p },
          properties: {}
        });
      }

      if (rulerPts.length >= 2) {
        feats.push({
          type: "Feature",
          geometry: { type: "LineString", coordinates: rulerPts },
          properties: {}
        });
      }

      src.setData({
        type: "FeatureCollection",
        features: feats
      });

      const tickFeatures = buildKilometerTickFeatures(rulerPts, geod);
      srcTicks.setData({
        type: "FeatureCollection",
        features: tickFeatures
      });

      const dist = calcEllipsoidLen(rulerPts);
      if (rulerInfo) {
        rulerInfo.textContent = geod
          ? `Расстояние: ${formatDist(dist)}`
          : "Расстояние: GeographicLib не загружен";
      }
    }

    function setRulerState(on) {
      rulerOn = on;
      if (btnToggle) btnToggle.textContent = `Линейка: ${rulerOn ? "вкл" : "выкл"}`;
      map.getCanvas().style.cursor = rulerOn ? "crosshair" : "";

      if (rulerInfo) {
        rulerInfo.style.display = rulerOn ? "block" : "none";
      }
    }

    if (btnToggle) {
      btnToggle.addEventListener("click", () => setRulerState(!rulerOn));
    }

    if (btnClear) {
      btnClear.addEventListener("click", () => {
        rulerPts = [];
        refreshRulerLayer();
      });
    }

    map.on("click", (e) => {
      if (!rulerOn) return;
      rulerPts.push([e.lngLat.lng, e.lngLat.lat]);
      refreshRulerLayer();
    });

    map.on("contextmenu", (e) => {
      if (!rulerOn) return;
      e.preventDefault();
      if (rulerPts.length > 0) {
        rulerPts.pop();
        refreshRulerLayer();
      }
    });

    map.on("load", function () {
      // basemap initial
      setBasemap("google_hybrid");

      // fit bounds
      const all = [...(SRC || []), ...(TGT || [])]
        .filter(p => Number.isFinite(Number(p.lon)) && Number.isFinite(Number(p.lat)));

      if (all.length > 0) {
        let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
        for (const p of all) {
          const lon = Number(p.lon), lat = Number(p.lat);
          minLon = Math.min(minLon, lon);
          minLat = Math.min(minLat, lat);
          maxLon = Math.max(maxLon, lon);
          maxLat = Math.max(maxLat, lat);
        }
        map.fitBounds([[minLon, minLat], [maxLon, maxLat]], { padding: 50, maxZoom: 17 });
      }

      // add ruler source/layers only after style load
      map.addSource("ruler", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] }
      });

      map.addLayer({
        id: "ruler-line",
        type: "line",
        source: "ruler",
        paint: {
          "line-color": "#7e57c2",
          "line-width": 2
        }
      });

      map.addLayer({
        id: "ruler-points",
        type: "circle",
        source: "ruler",
        paint: {
          "circle-radius": 4,
          "circle-color": "#7e57c2",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.2
        }
      });

      map.addSource("ruler_ticks", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] }
      });

      map.addLayer({
        id: "ruler-ticks",
        type: "line",
        source: "ruler_ticks",
        paint: {
          "line-color": "#000000",
          "line-width": 1.5
        },
        filter: ["==", ["get", "kind"], "tick"],
      });

      map.addLayer({
        id: "ruler-tick-labels",
        type: "symbol",
        source: "ruler_ticks",
        layout: {
          "text-field": ["concat", ["to-string", ["get", "km"]], " км"],
          "text-size": 11,
          "text-offset": [0, 0.9],
          "text-anchor": "top",
          "symbol-placement": "point"
        },
        paint: {
          "text-color": "#111111",
          "text-halo-color": "#ffffff",
          "text-halo-width": 1.0
        },
        filter: ["==", ["get", "kind"], "label"],
      });

      refreshRulerLayer();
    });

    const bmSelect = document.getElementById("basemapSelect");
    if (bmSelect) {
      bmSelect.addEventListener("change", function (e) {
        setBasemap(e.target.value);
      });
    }
  })();
  </script>
</body>
</html>