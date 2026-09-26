"""
core/user_transforms_db.py — пользовательская БД сохранённых параметров
перехода (не путать с core/crs_database.py — combined_crs.db read-only и
бандлится с приложением; эта БД пишется пользователем в %APPDATA%).

Параметры хранятся одним JSON-полем (params_json), а не отдельными
REAL-колонками — чтобы схема пережила будущие модели преобразования
(3/12 параметров, Молоденского-Бадекаса и т.п.) без миграции старых
записей: каждая модель — своё значение `method` + своя форма JSON.
Сейчас поддерживается только классический 7-параметровый Гельмерт
(Position Vector, source->target, канонический вид TransformationParams).

Пресет НЕ привязан к конкретной паре СК — это просто числа + текстовое
описание для человека. Пресеты группируются по категориям (category_id,
NULL = «Без категории» — не отдельная строка, просто отсутствие связи).
Системные категории/пресеты (is_system=1) — предзаполненные параметры по
ГОСТам, неудаляемые и неперемещаемые.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from core.constants import FACTOR_TO_PPM, ARCSEC_TO_RAD
from core.models import TransformationParams
from utils.user_data import get_user_data_dir

DB_FILENAME = "transforms.db"
SCHEMA_VERSION = 2

HELMERT7 = "helmert7_position_vector"

METHOD_LABELS = {
    HELMERT7: "7 параметров (Гельмерт, Position Vector)",
}

NO_CATEGORY_LABEL = "Без категории"


@dataclass
class Category:
    id: Optional[int]
    name: str
    is_system: bool
    sort_order: int = 0


@dataclass
class TransformPreset:
    id: Optional[int]
    name: str
    description: str
    method: str
    params: dict
    created_at: str
    category_id: Optional[int] = None
    is_system: bool = False

    @property
    def method_label(self) -> str:
        return METHOD_LABELS.get(self.method, f"Неизвестный формат ({self.method})")

    @property
    def is_supported(self) -> bool:
        return self.method == HELMERT7

    def to_transformation_params(self) -> TransformationParams:
        if self.method != HELMERT7:
            raise ValueError(f"Формат параметров не поддерживается: {self.method}")
        return helmert7_from_json(self.params)


# ── Кодек для helmert7_position_vector ────────────────────────────────────────

def helmert7_to_json(params: TransformationParams) -> dict:
    return {
        "dx": params.dx, "dy": params.dy, "dz": params.dz,
        "rx_sec": params.rx_sec, "ry_sec": params.ry_sec, "rz_sec": params.rz_sec,
        "scale_ppm": params.scale_ppm,
    }


def helmert7_from_json(d: dict) -> TransformationParams:
    return TransformationParams(
        dx=float(d["dx"]), dy=float(d["dy"]), dz=float(d["dz"]),
        rx=float(d["rx_sec"]) * ARCSEC_TO_RAD,
        ry=float(d["ry_sec"]) * ARCSEC_TO_RAD,
        rz=float(d["rz_sec"]) * ARCSEC_TO_RAD,
        scale=1.0 + float(d["scale_ppm"]) / FACTOR_TO_PPM,
    )


# ── Соединение / схема ────────────────────────────────────────────────────────

def _get_db_path():
    return get_user_data_dir() / DB_FILENAME


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(_get_db_path()))
    con.execute("""
        CREATE TABLE IF NOT EXISTS presets (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            description  TEXT NOT NULL DEFAULT '',
            method       TEXT NOT NULL,
            params_json  TEXT NOT NULL,
            created_at   TEXT NOT NULL
        )
    """)

    version = con.execute("PRAGMA user_version").fetchone()[0]

    if version < 2:
        _migrate_to_v2(con)
        con.execute("PRAGMA user_version = 2")

    con.commit()
    return con


def _migrate_to_v2(con: sqlite3.Connection) -> None:
    """Категории + системность пресетов, плюс посев системных ГОСТ-данных."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            is_system   INTEGER NOT NULL DEFAULT 0,
            sort_order  INTEGER NOT NULL DEFAULT 0
        )
    """)

    existing_cols = {row[1] for row in con.execute("PRAGMA table_info(presets)")}
    if "category_id" not in existing_cols:
        con.execute("ALTER TABLE presets ADD COLUMN category_id INTEGER")
    if "is_system" not in existing_cols:
        con.execute("ALTER TABLE presets ADD COLUMN is_system INTEGER NOT NULL DEFAULT 0")

    _seed_system_data(con)


# ── API: категории ────────────────────────────────────────────────────────────

def list_categories() -> List[Category]:
    con = _connect()
    try:
        rows = con.execute(
            "SELECT id, name, is_system, sort_order FROM categories "
            "ORDER BY sort_order, name"
        ).fetchall()
    finally:
        con.close()
    return [Category(id=r[0], name=r[1], is_system=bool(r[2]), sort_order=r[3]) for r in rows]


def create_category(name: str) -> int:
    con = _connect()
    try:
        cur = con.execute(
            "INSERT INTO categories (name, is_system, sort_order) VALUES (?, 0, 999)",
            (name,),
        )
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def rename_category(category_id: int, new_name: str) -> None:
    con = _connect()
    try:
        row = con.execute("SELECT is_system FROM categories WHERE id = ?", (category_id,)).fetchone()
        if row is None:
            raise ValueError("Категория не найдена.")
        if row[0]:
            raise ValueError("Системную категорию нельзя переименовать.")
        con.execute("UPDATE categories SET name = ? WHERE id = ?", (new_name, category_id))
        con.commit()
    finally:
        con.close()


def delete_category(category_id: int) -> None:
    con = _connect()
    try:
        row = con.execute("SELECT is_system FROM categories WHERE id = ?", (category_id,)).fetchone()
        if row is None:
            raise ValueError("Категория не найдена.")
        if row[0]:
            raise ValueError("Системную категорию нельзя удалить.")
        con.execute("UPDATE presets SET category_id = NULL WHERE category_id = ?", (category_id,))
        con.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        con.commit()
    finally:
        con.close()


# ── API: пресеты ──────────────────────────────────────────────────────────────

def list_presets() -> List[TransformPreset]:
    con = _connect()
    try:
        rows = con.execute(
            "SELECT id, name, description, method, params_json, created_at, "
            "category_id, is_system FROM presets ORDER BY created_at DESC"
        ).fetchall()
    finally:
        con.close()

    result = []
    for row in rows:
        try:
            params = json.loads(row[4])
        except (json.JSONDecodeError, TypeError):
            params = {}
        result.append(TransformPreset(
            id=row[0], name=row[1], description=row[2],
            method=row[3], params=params, created_at=row[5],
            category_id=row[6], is_system=bool(row[7]),
        ))
    return result


def save_preset(
    name: str, description: str, method: str, params: dict,
    category_id: Optional[int] = None,
) -> int:
    con = _connect()
    try:
        cur = con.execute(
            "INSERT INTO presets (name, description, method, params_json, created_at, category_id, is_system) "
            "VALUES (?, ?, ?, ?, ?, ?, 0)",
            (name, description, method, json.dumps(params),
             datetime.now(timezone.utc).isoformat(timespec="seconds"), category_id),
        )
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def update_preset(
    preset_id: int, name: str, description: str, category_id: Optional[int],
    method: str, params: dict,
) -> None:
    con = _connect()
    try:
        row = con.execute("SELECT is_system FROM presets WHERE id = ?", (preset_id,)).fetchone()
        if row is None:
            raise ValueError("Пресет не найден.")
        if row[0]:
            raise ValueError("Системный пресет нельзя редактировать.")
        con.execute(
            "UPDATE presets SET name = ?, description = ?, category_id = ?, "
            "method = ?, params_json = ? WHERE id = ?",
            (name, description, category_id, method, json.dumps(params), preset_id),
        )
        con.commit()
    finally:
        con.close()


def update_preset_category(preset_id: int, category_id: Optional[int]) -> None:
    """Используется drag&drop в дереве категорий."""
    con = _connect()
    try:
        row = con.execute("SELECT is_system FROM presets WHERE id = ?", (preset_id,)).fetchone()
        if row is None:
            raise ValueError("Пресет не найден.")
        if row[0]:
            raise ValueError("Системный пресет нельзя перемещать между категориями.")
        con.execute("UPDATE presets SET category_id = ? WHERE id = ?", (category_id, preset_id))
        con.commit()
    finally:
        con.close()


def delete_preset(preset_id: int) -> None:
    con = _connect()
    try:
        row = con.execute("SELECT is_system FROM presets WHERE id = ?", (preset_id,)).fetchone()
        if row is None:
            return
        if row[0]:
            raise ValueError("Системный пресет нельзя удалить.")
        con.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
        con.commit()
    finally:
        con.close()


# ── Системные данные (ГОСТ) ───────────────────────────────────────────────────

def _cf(dx, dy, dz, rx, ry, rz, m) -> dict:
    """
    Строка ИСТОЧНИКА дана в конвенции Coordinate Frame (EPSG:1032) —
    конвертируем в канонический Position Vector (EPSG:1033), в котором
    везде в приложении хранятся TransformationParams: знаки поворотов
    инвертируются, сдвиги/масштаб не меняются.
    """
    return {"dx": dx, "dy": dy, "dz": dz, "rx_sec": -rx, "ry_sec": -ry, "rz_sec": -rz, "scale_ppm": m}


def _seed_system_data(con: sqlite3.Connection) -> None:
    # Если системные категории уже есть — сид уже применялся, выходим.
    if con.execute("SELECT 1 FROM categories WHERE is_system = 1 LIMIT 1").fetchone():
        return

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _add_category(name: str, sort_order: int) -> int:
        cur = con.execute(
            "INSERT INTO categories (name, is_system, sort_order) VALUES (?, 1, ?)",
            (name, sort_order),
        )
        return cur.lastrowid

    def _add_preset(category_id: int, name: str, description: str, params: dict) -> None:
        con.execute(
            "INSERT INTO presets (name, description, method, params_json, created_at, category_id, is_system) "
            "VALUES (?, ?, ?, ?, ?, ?, 1)",
            (name, description, HELMERT7, json.dumps(params), now, category_id),
        )

    cat_2017 = _add_category("ГОСТ 32453-2017 (актуальный)", 0)
    cat_old = _add_category("ГОСТ Р 51794 (устаревшие)", 1)

    src_2017 = (
        "Источник: ГОСТ 32453-2017 (параметры получены суммированием переходов "
        "через ПЗ-90.11 → WGS-84). Метод в источнике: Coordinate Frame Rotation "
        "(EPSG:1032) — сконвертировано в Position Vector для хранения."
    )

    _add_preset(cat_2017, "ПЗ-90 → WGS-84 (ГОСТ 32453-2017)", src_2017,
                _cf(-1.43, 0.05, 0.20, 0, 0, -0.13, -0.22))
    _add_preset(cat_2017, "ПЗ-90.02 → WGS-84 (ГОСТ 32453-2017)", src_2017,
                _cf(-0.36, 0.08, 0.18, 0, 0, 0, 0))
    _add_preset(cat_2017, "ПЗ-90.11 → WGS-84 (ГОСТ 32453-2017)", src_2017,
                _cf(0.013, -0.106, -0.022, 0.0023, -0.00354, 0.00421, 0.008))
    _add_preset(cat_2017, "СК-42 → WGS-84 (ГОСТ 32453-2017)",
                src_2017 + " Эллипсоид Красовского.",
                _cf(23.57, -140.95, -79.80, 0, -0.35, -0.79, -0.22))
    _add_preset(cat_2017, "СК-95 → WGS-84 (ГОСТ 32453-2017)",
                src_2017 + " Эллипсоид Красовского.",
                _cf(24.47, -130.89, -81.56, 0, 0, -0.13, -0.22))
    _add_preset(cat_2017, "ГСК-2011 → WGS-84 (ГОСТ 32453-2017)",
                src_2017 + " Эллипсоид ГСК-2011.",
                _cf(0.013, -0.092, -0.030, 0.001738, -0.003559, 0.004263, 0.0074))

    _add_preset(
        cat_old, "СК-42 → WGS-84 (ГОСТ 51794-2001 = EPSG:1267 = MapInfo 1013)",
        "Источник: ГОСТ Р 51794-2001 / EPSG:1267 (Coordinate Frame Rotation, "
        "проверено напрямую по реестру epsg.io — в файле-заметке знаки ωy/ωz "
        "были без минуса, похоже на опечатку; здесь взяты значения из реестра). "
        "Совпадает с MapInfo 1013.",
        _cf(23.92, -141.27, -80.9, 0, -0.35, -0.82, -0.12),
    )
    _add_preset(
        cat_old, "СК-42 → WGS-84 (EPSG:15865)",
        "Источник: EPSG:15865 (Coordinate Frame Rotation, проверено по реестру epsg.io).",
        _cf(25, -141, -78.5, 0, -0.35, -0.736, 0),
    )
    _add_preset(
        cat_old, "СК-42 → ПЗ-90 (ГОСТ 51794-2001 = EPSG:15844 = ГОСТ 51794-2008 Прил.Б)",
        "Источник: ГОСТ Р 51794-2001/2008 / EPSG:15844 (Coordinate Frame Rotation, "
        "проверено по реестру epsg.io). В ГОСТ 51794-2001 указана точность "
        "±2 м / ±3 м (Z) / ±0.1″ / ±0.25 ppm.",
        _cf(25, -141, -80, 0, -0.35, -0.66, 0),
    )
    _add_preset(
        cat_old, "СК-42 → ПЗ-90.02 (ГОСТ 51794-2008, Прил. А)",
        "Источник: ГОСТ Р 51794-2008, приложение А. EPSG-код не найден; "
        "конвенция (Coordinate Frame) принята по аналогии — ωy/ωz/масштаб "
        "совпадают со строкой СК-42 в ГОСТ 32453-2017.",
        _cf(23.93, -141.03, -79.98, 0, -0.35, -0.79, -0.22),
    )
    _add_preset(
        cat_old, "СК-95 → ПЗ-90.02 (ГОСТ 51794-2008, Прил. А)",
        "Источник: ГОСТ Р 51794-2008, приложение А. EPSG-код не найден; "
        "конвенция (Coordinate Frame) принята по аналогии — ωz/масштаб "
        "совпадают со строкой СК-95 в ГОСТ 32453-2017.",
        _cf(24.83, -130.97, -81.74, 0, 0, -0.13, -0.22),
    )
    _add_preset(
        cat_old, "СК-95 → WGS-84 (MapInfo 1014)",
        "Источник: MapInfo 1014 (совпадает с ГОСТ 51794-2001 в разделе "
        "«Дополнительно» исходной заметки). MapInfo Pro использует Coordinate "
        "Frame Rotation.",
        _cf(24.82, -131.21, -82.66, 0, 0, -0.16, -0.12),
    )
    _add_preset(
        cat_old, "ПЗ-90 → WGS-84 (EPSG:15843)",
        "Источник: EPSG:15843 (Coordinate Frame Rotation, проверено по реестру epsg.io).",
        _cf(0, 0, 1.5, 0, 0, -0.076, 0),
    )
    _add_preset(
        cat_old, "ПЗ-90 → WGS-84 (ГОСТ 51794-2001 = EPSG:1244 = MapInfo 1012)",
        "Источник: ГОСТ Р 51794-2001 / EPSG:1244 (Coordinate Frame Rotation, "
        "проверено по реестру epsg.io). Указана точность ±0.2 м / ±0.3 м (Z) "
        "/ ±0.1″ / ±0.06 ppm.",
        _cf(-1.08, -0.27, -0.9, 0, 0, -0.16, -0.12),
    )
    _add_preset(
        cat_old, "ПЗ-90 → WGS-84 (ГОСТ 51794-2008, Прил. Г)",
        "Источник: ГОСТ Р 51794-2008, приложение Г. EPSG-код не найден; "
        "конвенция (Coordinate Frame) принята по аналогии с EPSG:1244 — "
        "это уточнённая версия того же перехода. Указана точность ωz ±0.01″.",
        _cf(-1.10, -0.30, -0.90, 0, 0, -0.20, -0.12),
    )
