import numpy as np

# Угловые константы
RAD_TO_DEG = 180.0 / np.pi
DEG_TO_RAD = np.pi / 180.0

# Секунды
ARCSEC_TO_RAD = np.pi / (180.0 * 3600.0)  # 1 секунда в радианах
RAD_TO_ARCSEC = 1.0 / ARCSEC_TO_RAD        # 1 радиан в секундах (примерно 206265)

# Масштабные коэффициенты
PPM_TO_FACTOR = 1e-6                        # ppm в коэффициент
FACTOR_TO_PPM = 1e6                         # коэффициент в ppm
PPB_TO_FACTOR = 1e-9                        # ppb в коэффициент
FACTOR_TO_PPB = 1e9                          # коэффициент в ppb

# Точность
EPSILON = 1e-10                              # машинный ноль для сравнений