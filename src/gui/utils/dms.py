import re
from typing import Optional

# ── DMS → DD (Degrees°Minutes'Seconds" → Decimal Degrees) ────────────────────

_DMS_DEG_CHARS      = frozenset('°∘度')
_DMS_MIN_CHARS      = frozenset("'′`´分")
_DMS_SEC_CHARS      = frozenset('"″秒')
_DMS_TYPEABLE_CHARS = frozenset("°'\" `´*NSEWnsew")  # ≤255, проходят EVT_CHAR

_RU_NEG_RE = re.compile(
    r'[юЮ]\.?\s*[шШ]\.?|[зЗ]\.?\s*[дД]\.?', re.UNICODE
)
_RU_POS_RE = re.compile(
    r'[сС]\.?\s*[шШ]\.?|[вВ]\.?\s*[дД]\.?', re.UNICODE
)
_HAS_DMS_SYM_RE = re.compile(r'[°∘度′分秒\'"`´″*]')


def _format_dd(dd: float, dec_sep: str) -> str:
    """Форматирует десятичные градусы: до 8 знаков, без хвостовых нулей."""
    result = f"{dd:.8f}".rstrip('0').rstrip('.')
    if dec_sep == ',':
        result = result.replace('.', ',')
    return result


def _try_dms_to_dd(raw: str, dec_sep: str = '.') -> Optional[str]:
    """
    Пытается распознать строку как координату в формате ГГ°ММ'СС.СС"
    и конвертирует в десятичные градусы.
    Возвращает строку или None, если формат не похож на DMS.

    Поддерживаемые форматы:
        43°34'45.12"        43° 34' 45"       43°34'45
        43度34分45.12秒       N 43°34'45"       43°34'45" S
        43°34'45" с.ш.      W054°18'24"       -43°34'45"
        25'46"  (без символа градусов, но есть и минуты, и секунды)
        43°34.567'          (десятичные минуты)
    """
    text = raw.strip()
    if not text:
        return None

    # Быстрая проверка: нужен хотя бы символ градусов ИЛИ оба (минут И секунд)
    has_deg = bool(set(text) & _DMS_DEG_CHARS)
    has_min = bool(set(text) & _DMS_MIN_CHARS)
    has_sec = bool(set(text) & _DMS_SEC_CHARS)
    has_star = bool(re.search(r'\d\s*\*\s*\d', text))  # «*» как символ градусов

    if not has_deg and not has_star and not (has_min and has_sec):
        return None

    # ── Определяем знак по полушарию ─────────────────────────────────────────
    sign    = 1
    working = text

    # Русские суффиксы (многосимвольные — проверяем первыми)
    if _RU_NEG_RE.search(working):
        sign    = -1
        working = _RU_NEG_RE.sub('', working).strip()
    elif _RU_POS_RE.search(working):
        sign    = 1
        working = _RU_POS_RE.sub('', working).strip()

    # Латинский NSEW — префикс (N43°... или N 43°...)
    m = re.match(r'^([NSEWnsew])\s*(.+)', working, re.DOTALL)
    if m and _HAS_DMS_SYM_RE.search(m.group(2)):
        hemi    = m.group(1).upper()
        sign    = -1 if hemi in ('S', 'W') else 1
        working = m.group(2).strip()
    else:
        # Латинский NSEW — суффикс (...43°34'45" W)
        m = re.match(r'^(.+?)\s*([NSEWnsew])\s*$', working, re.DOTALL)
        if m and _HAS_DMS_SYM_RE.search(m.group(1)):
            hemi    = m.group(2).upper()
            sign    = -1 if hemi in ('S', 'W') else 1
            working = m.group(1).strip()

    # Явный минус в начале (-43°34'45")
    working = working.strip()
    if working.startswith('-'):
        sign   *= -1
        working = working[1:].strip()

    # ── Извлекаем числа ───────────────────────────────────────────────────────
    working_dot = working.replace(',', '.')          # унифицируем разделитель
    nums = re.findall(r'\d+(?:\.\d+)?', working_dot)

    # Только один токен + символ градусов → «25°» = просто 25 градусов
    if len(nums) == 1 and (has_deg or has_star):
        try:
            return _format_dd(float(nums[0]) * sign, dec_sep)
        except ValueError:
            return None

    if len(nums) < 2:
        return None

    try:
        deg  = float(nums[0])
        mins = float(nums[1])
        secs = float(nums[2]) if len(nums) >= 3 else 0.0
    except (ValueError, IndexError):
        return None

    # Проверка физических диапазонов
    if not (0 <= deg <= 360 and 0 <= mins < 60 and 0 <= secs < 60):
        return None

    dd = (deg + mins / 60.0 + secs / 3600.0) * sign
    return _format_dd(dd, dec_sep)
