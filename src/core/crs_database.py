"""
Доступ к базе combined_crs.db.
Таблица crs: code, name, type, category, subcategory, wkt, proj4,
             area_of_use, datum, ellipsoid, deprecated
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional

# ── Человекочитаемые названия подкатегорий (проецированные) ──────────────────

SUBCAT_LABELS: Dict[str, str] = {
    "utm":              "UTM",
    "msk":              "МСК субъектов РФ",
    "pulkovo":          "Пулково / СК-42 / СК-95",
    "gauss_kruger":     "Гаусса-Крюгера",
    "tmerc":            "Поперечная Меркатора",
    "lcc":              "Коническая Ламберта (LCC)",
    "merc":             "Меркатора",
    "stere":            "Стереографическая",
    "aea":              "Равноплощадная Альберса",
    "eqc":              "Равнопромежуточная цилиндрическая",
    "cass":             "Кассини-Зольднера",
    "krovak":           "Кровака",
    "poly":             "Поликоническая",
    "ortho":            "Ортографическая",
    "other_projection": "Другие проекции",
    "other_datum":      "Другие датумы",
    "other":            "Прочие",
}

# Порядок подкатегорий проецированных СК
SUBCAT_ORDER = [
    "msk",
    # Специальные datum-подкатегории для проецированных (добавлены вручную)
    "_pulkovo_1942", "_pulkovo_1995", "_gsk_2011",
    "pulkovo", "gauss_kruger", "utm", "tmerc",
    "lcc", "merc", "stere", "aea", "eqc",
    "cass", "krovak", "poly", "ortho",
    "other_projection", "other_datum", "other",
]

# Человекочитаемые метки специальных datum-подкатегорий
_SPECIAL_PROJ_LABELS: Dict[str, str] = {
    "_pulkovo_1942": "Пулково 1942",
    "_pulkovo_1995": "Пулково 1995",
    "_gsk_2011":     "ГСК-2011",
}

# Приоритет датумов для сортировки географических СК
_GEO_DATUM_PRIORITY: Dict[str, int] = {
    "WGS 84":       0,
    "Pulkovo 1942": 1,
    "Pulkovo 1995": 2,
    "GSK-2011":     3,
}


@dataclass
class CrsEntry:
    code:        int
    name:        str
    crs_type:    str
    subcategory: str
    wkt:         str
    proj4:       str
    area:        str
    datum:       str
    ellipsoid:   str

    @property
    def label(self) -> str:
        if self.code and self.subcategory != "msk":
            suffix = f"  [EPSG:{self.code}]"
        else:
            suffix = ""
        return f"{self.name}{suffix}"

    @property
    def crs_source(self) -> str:
        """WKT если есть, иначе Proj4."""
        return self.wkt or self.proj4


# ── Поиск базы данных ─────────────────────────────────────────────────────────

_DB_PATH: Optional[str] = None


def get_db_path() -> Optional[str]:
    global _DB_PATH
    if _DB_PATH and os.path.isfile(_DB_PATH):
        return _DB_PATH
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.normpath(os.path.join(here, "..", "..", "resources", "combined_crs.db")),
        os.path.normpath(os.path.join(here, "..", "..", "..", "resources", "combined_crs.db")),
        os.path.join(os.path.dirname(here), "resources", "combined_crs.db"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            _DB_PATH = c
            return c
    return None


def set_db_path(path: str):
    global _DB_PATH
    _DB_PATH = path


# ── Загрузка ──────────────────────────────────────────────────────────────────

def load_all_entries(db_path: Optional[str] = None) -> List[CrsEntry]:
    if db_path is None:
        db_path = get_db_path()
    if db_path is None:
        return []

    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("""
            SELECT
                COALESCE(code, 0),
                COALESCE(name, ''),
                COALESCE(type, ''),
                COALESCE(subcategory, 'other'),
                COALESCE(wkt,  ''),
                COALESCE(proj4,''),
                COALESCE(area_of_use, ''),
                COALESCE(datum,    ''),
                COALESCE(ellipsoid,'')
            FROM crs
            WHERE (deprecated = 0 OR deprecated IS NULL)
              AND (wkt != '' OR proj4 != '')
            ORDER BY type DESC, subcategory, name
        """)
        rows = cur.fetchall()
        con.close()
    except sqlite3.Error:
        return []

    return [
        CrsEntry(
            code        = int(row[0]),
            name        = row[1],
            crs_type    = row[2],
            subcategory = row[3],
            wkt         = row[4],
            proj4       = row[5],
            area        = row[6],
            datum       = row[7],
            ellipsoid   = row[8],
        )
        for row in rows
    ]


# ── Фильтрация в памяти ───────────────────────────────────────────────────────

def filter_entries(
    entries:             List[CrsEntry],
    query:               str  = "",
    include_projected:   bool = True,
    include_geographic:  bool = True,
) -> List[CrsEntry]:
    """Фильтрует загруженные записи по строке и типу."""
    q = query.strip().lower()
    result = []
    for e in entries:
        is_proj = "projected" in e.crs_type
        is_geo  = "geographic" in e.crs_type or "geodetic" in e.crs_type
        if is_proj and not include_projected:
            continue
        if is_geo and not include_geographic:
            continue
        if q and q not in e.name.lower() and q not in str(e.code):
            continue
        result.append(e)
    return result


# ── Группировка ───────────────────────────────────────────────────────────────

def _proj_subcat_key(e: CrsEntry) -> str:
    """
    Определяет ключ подкатегории для проецированной СК.
    Приоритет: специальные datum-подкатегории → штатная subcategory из БД.
    """
    name = e.name
    if "Pulkovo 1942" in name:
        return "_pulkovo_1942"
    if "Pulkovo 1995" in name:
        return "_pulkovo_1995"
    if "GSK-2011" in name:
        return "_gsk_2011"
    return e.subcategory


def _proj_subcat_label(key: str) -> str:
    if key in _SPECIAL_PROJ_LABELS:
        return _SPECIAL_PROJ_LABELS[key]
    return SUBCAT_LABELS.get(key, key.replace("_", " ").capitalize())


def _geo_subcat_label(e: CrsEntry) -> str:
    """Для географических СК — подкатегория по полю datum."""
    datum = e.datum.strip()
    return datum if datum else "Прочие"


def group_entries(
    entries: List[CrsEntry],
) -> Dict[str, Dict[str, List[CrsEntry]]]:
    """
    Группирует записи по типу и подкатегории.

    Проецированные: subcategory из БД, с выделением Pulkovo 1942 / 1995 / GSK-2011
                    по имени в отдельные подкатегории.
    Географические: группировка по полю datum (а не subcategory).
    Геоцентрические / Прочие: включаются в словарь, но скрываются в UI.

    Возвращает: {type_label: {subcat_label: [entries]}}
    """
    TYPE_LABELS = {
        "projected":  "Проецированные",
        "geographic": "Географические",
        "geocentric": "Геоцентрические",
        "other":      "Прочие",
    }

    grouped: Dict[str, Dict[str, List[CrsEntry]]] = {}

    for e in entries:
        t = e.crs_type.lower()
        if "projected" in t:
            type_key     = "projected"
            subcat_label = _proj_subcat_label(_proj_subcat_key(e))
        elif "geographic" in t or "geodetic" in t:
            type_key     = "geographic"
            subcat_label = _geo_subcat_label(e)
        elif "geocentric" in t:
            type_key     = "geocentric"
            subcat_label = SUBCAT_LABELS.get(e.subcategory, "Прочие")
        else:
            type_key     = "other"
            subcat_label = SUBCAT_LABELS.get(e.subcategory, "Прочие")

        type_label = TYPE_LABELS.get(type_key, type_key.capitalize())
        grouped.setdefault(type_label, {}).setdefault(subcat_label, []).append(e)

    # ── Сортировка подкатегорий ───────────────────────────────────────────────

    # Порядковый индекс для проецированных (по SUBCAT_ORDER)
    _proj_order: Dict[str, int] = {}
    for i, k in enumerate(SUBCAT_ORDER):
        label = _SPECIAL_PROJ_LABELS.get(k) or SUBCAT_LABELS.get(k, k)
        _proj_order[label] = i

    for type_label, subcats in grouped.items():
        if type_label == "Проецированные":
            grouped[type_label] = dict(
                sorted(subcats.items(),
                       key=lambda kv: (_proj_order.get(kv[0], 999), kv[0]))
            )
        elif type_label == "Географические":
            # WGS 84 → Pulkovo → GSK → остальные по алфавиту
            def _geo_sort(kv: tuple) -> tuple:
                label = kv[0]
                for datum_substr, pri in _GEO_DATUM_PRIORITY.items():
                    if datum_substr in label:
                        return (pri, label)
                return (99, label)
            grouped[type_label] = dict(sorted(subcats.items(), key=_geo_sort))
        else:
            grouped[type_label] = dict(sorted(subcats.items(), key=lambda kv: kv[0]))

    return grouped
