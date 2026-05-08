# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QScrollArea,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox,
    QRadioButton, QButtonGroup, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QListWidget, QListWidgetItem,
    QTabWidget, QSizePolicy, QStatusBar,
    QAbstractItemView, QToolBar, QToolButton,
)


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("section_title")
    return lbl

def _result_section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("result_section_title")
    return lbl

def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFrameShadow(QFrame.Shadow.Plain)
    return f

def _vline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setFrameShadow(QFrame.Shadow.Plain)
    return f

def _tb_btn(text: str, tooltip: str = "", danger: bool = False) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("tb_btn_danger" if danger else "tb_btn")
    btn.setToolTip(tooltip)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return btn

def _crs_card(parent: QWidget) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame(parent)
    card.setObjectName("crs_card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(10, 8, 10, 10)
    layout.setSpacing(6)
    return card, layout


class BaseMainFrame(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Easy Helmert")
        self.resize(1280, 820)
        self.setMinimumSize(900, 600)
        self._build_menu()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._configure_splitters()

    # ── Меню ─────────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()
        mb.setNativeMenuBar(False)

        m_file = mb.addMenu("Файл")
        self.action_new        = m_file.addAction("Новый расчёт");          self.action_new.setShortcut("Ctrl+N")
        self.action_import_txt = m_file.addAction("Импорт координат из текстового файла..."); self.action_import_txt.setShortcut("Ctrl+O")
        self.action_import_cal = m_file.addAction("Импорт калибровки...")
        m_file.addSeparator()
        self.action_save_table = m_file.addAction("Сохранить таблицу в файл..."); self.action_save_table.setShortcut("Ctrl+S")
        self.action_export_cal = m_file.addAction("Сохранить таблицу как калибровку...")
        self.action_show_map   = m_file.addAction("Показать точки на карте..."); self.action_show_map.setShortcut("Ctrl+M")
        m_file.addSeparator()
        self.action_exit       = m_file.addAction("Выход"); self.action_exit.setShortcut("Ctrl+Q")

        m_table = mb.addMenu("Таблица")
        self.action_swapxy_src    = m_table.addAction("Переставить север/восток у исходных точек")
        self.action_swapxy_tgt    = m_table.addAction("Переставить север/восток у опорных точек")
        m_table.addSeparator()
        self.action_parse_degrees = m_table.addAction("Парсинг градусных координат")

        m_params = mb.addMenu("Вычисленные параметры")
        self.action_save_wkt1  = m_params.addAction("Сохранить как WKT...")
        self.action_save_wkt2  = m_params.addAction("Сохранить как WKT2...")
        self.action_save_proj4 = m_params.addAction("Сохранить как Proj4...")
        m_params.addSeparator()
        self.action_copy_wkt1  = m_params.addAction("Копировать WKT в буфер обмена")
        self.action_copy_wkt2  = m_params.addAction("Копировать WKT2 в буфер обмена")
        self.action_copy_proj4 = m_params.addAction("Копировать Proj4 в буфер обмена")

        m_prog = mb.addMenu("Программа")
        self.action_about = m_prog.addAction("О программе")

    # ── Тулбар ───────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        tb = QToolBar("Основной", self)
        tb.setObjectName("main_toolbar")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setIconSize(QSize(22, 22))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(tb)
        self._main_toolbar = tb

        def _svg_icon(paths_d: list[str], color: str = "#cdccca") -> "QIcon":
            from PySide6.QtGui import QIcon, QPixmap, QPainter
            from PySide6.QtSvg import QSvgRenderer
            from PySide6.QtCore import QByteArray
            paths_svg = "".join(
                f'<path d="{d}" stroke="{color}" stroke-width="1.5" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
                for d in paths_d
            )
            svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" '
                f'viewBox="0 0 24 24" fill="none">{paths_svg}</svg>'
            ).encode()
            renderer = QSvgRenderer(QByteArray(svg))
            px = QPixmap(22, 22); px.fill(Qt.GlobalColor.transparent)
            painter = QPainter(px); renderer.render(painter); painter.end()
            return QIcon(px)

        def _add(action, paths, label, obj=None, color="#cdccca"):
            btn = QToolButton()
            btn.setDefaultAction(action)
            btn.setIcon(_svg_icon(paths, color))
            btn.setText(label)
            if obj:
                btn.setObjectName(obj)
            tb.addWidget(btn)
            return btn

        _add(self.action_new,        ["M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z","M14 2v6h6","M12 18v-6","M9 15h6"], "Новый")
        _add(self.action_import_txt, ["M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"], "Открыть")
        _add(self.action_save_table, ["M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z","M17 21v-8H7v8","M7 3v5h8"], "Сохранить")
        tb.addSeparator()
        _add(self.action_import_cal, ["M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4","M7 10l5 5 5-5","M12 15V3"], "Импорт")
        _add(self.action_export_cal, ["M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4","M17 8l-5-5-5 5","M12 3v12"], "Экспорт")
        tb.addSeparator()

        btn_add = QToolButton()
        btn_add.setIcon(_svg_icon(["M12 5v14","M5 12h14"]))
        btn_add.setText("Добавить"); btn_add.setObjectName("tb_add_point")
        btn_add.setToolTip("Добавить строку в таблицу")
        tb.addWidget(btn_add); self.btn_add_row_tb = btn_add

        btn_del = QToolButton()
        btn_del.setIcon(_svg_icon(["M3 6h18","M19 6l-1 14H6L5 6","M9 6V4h6v2"], "#c07070"))
        btn_del.setText("Удалить"); btn_del.setObjectName("tb_del_point")
        btn_del.setToolTip("Удалить выбранные строки")
        tb.addWidget(btn_del); self.btn_del_row_tb = btn_del

        tb.addSeparator()

        btn_sw1 = QToolButton()
        btn_sw1.setIcon(_svg_icon(["M7 16V4","M3 8l4-4 4 4","M17 8v12","M21 16l-4 4-4-4"], "#fdab43"))
        btn_sw1.setText("Из ПК → Исх."); btn_sw1.setObjectName("tb_btn_danger")
        btn_sw1.setToolTip("Переставить Север↔Восток у исходных точек")
        tb.addWidget(btn_sw1); self.btn_swap_src_tb = btn_sw1

        btn_sw2 = QToolButton()
        btn_sw2.setIcon(_svg_icon(["M17 16V4","M13 8l4-4 4 4","M7 8v12","M11 16l-4 4-4-4"], "#fdab43"))
        btn_sw2.setText("Исх. → ПК"); btn_sw2.setObjectName("tb_btn_danger")
        btn_sw2.setToolTip("Переставить Север↔Восток у опорных точек")
        tb.addWidget(btn_sw2); self.btn_swap_dst_tb = btn_sw2

        tb.addSeparator()
        _add(self.action_show_map, ["M1 6v16l7-4 8 4 7-4V2l-7 4-8-4-7 4","M8 2v16","M16 6v16"], "Карта")

        spacer = QToolButton()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setEnabled(False)
        spacer.setStyleSheet("background:transparent;border:none;")
        tb.addWidget(spacer)

        self.lbl_tb_total = QToolButton(); self.lbl_tb_total.setEnabled(False)
        self.lbl_tb_total.setText("Точек в таблице:  0"); self.lbl_tb_total.setObjectName("tb_info_label")
        self.lbl_tb_used  = QToolButton(); self.lbl_tb_used.setEnabled(False)
        self.lbl_tb_used.setText("Используется:  0"); self.lbl_tb_used.setObjectName("tb_info_label")
        tb.addWidget(self.lbl_tb_total)
        tb.addWidget(self.lbl_tb_used)

    # ── Центральный виджет ────────────────────────────────────────────────────

    def _build_central(self):
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(1)
        self.setCentralWidget(self.main_splitter)

        left = self._build_left_panel()
        left.setObjectName("left_panel")
        self.main_splitter.addWidget(left)

        right = self._build_right_area()
        right.setObjectName("right_panel")
        self.main_splitter.addWidget(right)

        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

    # ── Левая панель ─────────────────────────────────────────────────────────

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(340)
        panel.setMaximumWidth(440)

        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("left_scroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("left_scroll_content")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(14)

        vbox.addWidget(_section_label("Системы координат"))

        src_card, src_layout = _crs_card(content)
        lbl_src = QLabel("Исходная СК"); lbl_src.setObjectName("lbl_card_title_src")
        src_layout.addWidget(lbl_src)
        src_row = QHBoxLayout(); src_row.setSpacing(4)
        self.lbl_src_crs = QLineEdit(); self.lbl_src_crs.setReadOnly(True); self.lbl_src_crs.setPlaceholderText("Не выбрана")
        self.btn_set_src_crs = QPushButton("⚙"); self.btn_set_src_crs.setObjectName("btn_crs_pick"); self.btn_set_src_crs.setFixedSize(28, 28)
        src_row.addWidget(self.lbl_src_crs, 1); src_row.addWidget(self.btn_set_src_crs)
        src_layout.addLayout(src_row)
        geoid_src = QHBoxLayout(); geoid_src.setSpacing(6); geoid_src.addWidget(QLabel("Геоид:"))
        self.cmb_src_geoid = QComboBox(); self.cmb_src_geoid.addItems(["Ничего не делать","Прибавить EGM2008","Вычесть EGM2008"])
        geoid_src.addWidget(self.cmb_src_geoid, 1); src_layout.addLayout(geoid_src)
        self.chk_correction = QCheckBox("Исходные высоты на квазигеоиде\n(подогнать к геоиду)"); self.chk_correction.setEnabled(False)
        src_layout.addWidget(self.chk_correction)
        vbox.addWidget(src_card)

        tgt_card, tgt_layout = _crs_card(content)
        lbl_tgt = QLabel("Опорная СК"); lbl_tgt.setObjectName("lbl_card_title_tgt")
        tgt_layout.addWidget(lbl_tgt)
        tgt_row = QHBoxLayout(); tgt_row.setSpacing(4)
        self.lbl_tgt_crs = QLineEdit("WGS 84 [EPSG:4979]"); self.lbl_tgt_crs.setReadOnly(True)
        self.btn_set_tgt_crs = QPushButton("⚙"); self.btn_set_tgt_crs.setObjectName("btn_crs_pick"); self.btn_set_tgt_crs.setFixedSize(28, 28)
        tgt_row.addWidget(self.lbl_tgt_crs, 1); tgt_row.addWidget(self.btn_set_tgt_crs)
        tgt_layout.addLayout(tgt_row)
        geoid_tgt = QHBoxLayout(); geoid_tgt.setSpacing(6); geoid_tgt.addWidget(QLabel("Геоид:"))
        self.cmb_tgt_geoid = QComboBox(); self.cmb_tgt_geoid.addItems(["Не использовать (эллипс. высоты)","Прибавить EGM2008","Вычесть EGM2008"])
        geoid_tgt.addWidget(self.cmb_tgt_geoid, 1); tgt_layout.addLayout(geoid_tgt)
        vbox.addWidget(tgt_card)

        vbox.addWidget(_hline())
        vbox.addWidget(_section_label("Параметры трансформации"))

        self.rb_params_3  = QRadioButton("3 параметра (только сдвиг)")
        self.rb_params_7  = QRadioButton("7 параметров (Гельмерт)")
        self.rb_params_12 = QRadioButton("12 параметров")
        self.rb_params_7.setChecked(True)
        self._params_group = QButtonGroup(content)
        self._params_group.addButton(self.rb_params_3,  0)
        self._params_group.addButton(self.rb_params_7,  1)
        self._params_group.addButton(self.rb_params_12, 2)
        vbox.addWidget(self.rb_params_3)
        vbox.addWidget(self.rb_params_7)
        vbox.addWidget(self.rb_params_12)

        vbox.addWidget(_hline())

        self.btn_calculate = QPushButton("РАССЧИТАТЬ")
        self.btn_calculate.setObjectName("btn_calculate")
        self.btn_calculate.setMinimumHeight(36)
        vbox.addWidget(self.btn_calculate)

        self.btn_optimize = QPushButton("НАЙТИ ОПТИМУМ")
        self.btn_optimize.setObjectName("btn_optimize")
        self.btn_optimize.setMinimumHeight(32)
        vbox.addWidget(self.btn_optimize)

        vbox.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll)
        return panel

    # ── Правая область ───────────────────────────────────────────────────────

    def _build_right_area(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)

        tab_calc = QWidget()
        tab_layout = QVBoxLayout(tab_calc)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        tab_layout.addWidget(self._build_table_toolbar())

        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setHandleWidth(1)

        self.grid_placeholder = QWidget()
        self.grid_placeholder.setObjectName("grid_area")
        self.grid_placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.right_splitter.addWidget(self.grid_placeholder)
        self.right_splitter.addWidget(self._build_result_panel())
        self.right_splitter.setStretchFactor(0, 1)
        self.right_splitter.setStretchFactor(1, 0)

        tab_layout.addWidget(self.right_splitter, 1)
        self.tab_widget.addTab(tab_calc, "Расчёт параметров")
        self.tab_widget.addTab(QWidget(), "Калькулятор")
        self.tab_widget.addTab(QWidget(), "Преобразование геоида")
        self.tab_widget.addTab(QWidget(), "Карта")

        vbox.addWidget(self.tab_widget, 1)
        return container

    # ── Toolbar таблицы ───────────────────────────────────────────────────────

    def _build_table_toolbar(self) -> QWidget:
        toolbar = QWidget()
        toolbar.setObjectName("table_toolbar")
        toolbar.setFixedHeight(36)
        hbox = QHBoxLayout(toolbar)
        hbox.setContentsMargins(6, 0, 8, 0)
        hbox.setSpacing(2)

        self.btn_add_row  = _tb_btn("＋ Добавить", "Добавить строку")
        self.btn_del_row  = _tb_btn("− Удалить",   "Удалить выбранные строки")
        self.btn_row_up   = _tb_btn("↑", "Переместить строку вверх"); self.btn_row_up.setFixedWidth(28)
        self.btn_row_down = _tb_btn("↓", "Переместить строку вниз");  self.btn_row_down.setFixedWidth(28)
        for b in (self.btn_add_row, self.btn_del_row, self.btn_row_up, self.btn_row_down):
            hbox.addWidget(b)
        hbox.addWidget(_vline())

        self.btn_import = _tb_btn("⬆ Импорт", "Импортировать точки из файла")
        self.btn_export = _tb_btn("⬇ Экспорт", "Экспортировать таблицу")
        hbox.addWidget(self.btn_import); hbox.addWidget(self.btn_export)
        hbox.addWidget(_vline())

        self.btn_swap_src = _tb_btn("⇅ С↔В исх.",  "Переставить Север↔Восток в исходных", danger=True)
        self.btn_swap_dst = _tb_btn("⇅ С↔В опорн.","Переставить Север↔Восток в опорных",  danger=True)
        self.btn_dms_dd   = _tb_btn("° DMS→DD",     "Конвертировать градусные координаты",  danger=True)
        for b in (self.btn_swap_src, self.btn_swap_dst, self.btn_dms_dd):
            hbox.addWidget(b)
        hbox.addWidget(_vline())

        hbox.addWidget(QLabel("Порог:"))
        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setDecimals(2); self.spin_threshold.setRange(0, 100)
        self.spin_threshold.setValue(0.10);  self.spin_threshold.setFixedWidth(68)
        hbox.addWidget(self.spin_threshold)
        self.cmb_threshold_units = QComboBox(); self.cmb_threshold_units.addItems(["м","СКО"]); self.cmb_threshold_units.setFixedWidth(52)
        hbox.addWidget(self.cmb_threshold_units)
        hbox.addStretch(1)

        self.lbl_points_status = QLabel("Точек: 0 · Выбрано: 0")
        self.lbl_points_status.setObjectName("lbl_point_count")
        hbox.addWidget(self.lbl_points_status)
        return toolbar

    # ── Нижняя панель результатов ─────────────────────────────────────────────

    def _build_result_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("result_panel")
        panel.setMinimumHeight(180)

        hbox = QHBoxLayout(panel)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)

        self.results_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.results_splitter.setHandleWidth(1)
        hbox.addWidget(self.results_splitter)

        # ── Колонка 1: История ────────────────────────────────────────
        col1 = QWidget(); col1.setObjectName("result_col"); col1.setMinimumWidth(220); col1.setMaximumWidth(320)
        l1 = QVBoxLayout(col1); l1.setContentsMargins(10, 8, 8, 8); l1.setSpacing(5)
        l1.addWidget(_result_section("История вычислений"))
        self.history_list = QListWidget(); self.history_list.setObjectName("history_list")
        for e in ["24.05.2026 15:42 · 7 пар. · RMS 0.016", "24.05.2026 15:31 · 7 пар. · RMS 0.019", "24.05.2026 15:20 · 4 пар. · RMS 0.043"]:
            self.history_list.addItem(QListWidgetItem(e))
        self.history_list.setCurrentRow(0)
        l1.addWidget(self.history_list, 1)
        btn_row = QHBoxLayout()
        self.btn_history_apply  = QPushButton("✔ Применить")
        self.btn_history_delete = QPushButton("✕ Удалить")
        btn_row.addWidget(self.btn_history_apply); btn_row.addWidget(self.btn_history_delete)
        l1.addLayout(btn_row)
        self.results_splitter.addWidget(col1)

        # ── Колонка 2: Единый блок результатов ───────────────────────
        col2 = QWidget(); col2.setObjectName("result_col"); col2.setMinimumWidth(420)
        l2 = QVBoxLayout(col2); l2.setContentsMargins(0, 0, 0, 0); l2.setSpacing(0)

        # Заголовок
        header = QFrame(); header.setObjectName("result_block_header"); header.setFixedHeight(52)
        h_layout = QHBoxLayout(header); h_layout.setContentsMargins(12, 6, 12, 6); h_layout.setSpacing(8)

        title_col = QVBoxLayout(); title_col.setSpacing(2)
        self.lbl_calc_name   = QLabel("Без названия"); self.lbl_calc_name.setObjectName("lbl_calc_name")
        self.lbl_calc_method = QLabel("7 параметров (Гельмерт) · Исх → Опорн · Position Vector")
        self.lbl_calc_method.setObjectName("lbl_calc_method")
        title_col.addWidget(self.lbl_calc_name); title_col.addWidget(self.lbl_calc_method)
        h_layout.addLayout(title_col, 1)

        dt_col = QVBoxLayout(); dt_col.setSpacing(2)
        dt_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_calc_datetime = QLabel("24.05.2026  15:42:18")
        self.lbl_calc_datetime.setObjectName("lbl_calc_datetime")
        self.lbl_calc_datetime.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.btn_copy_all = QPushButton("⎘"); self.btn_copy_all.setObjectName("btn_copy_all")
        self.btn_copy_all.setToolTip("Скопировать все параметры"); self.btn_copy_all.setFixedSize(24, 20)
        dt_col.addWidget(self.lbl_calc_datetime)
        dt_col.addWidget(self.btn_copy_all, 0, Qt.AlignmentFlag.AlignRight)
        h_layout.addLayout(dt_col)
        l2.addWidget(header)
        l2.addWidget(_hline())

        # Тело: три подсекции
        body = QWidget(); body.setObjectName("result_body")
        body_hbox = QHBoxLayout(body); body_hbox.setContentsMargins(0, 0, 0, 0); body_hbox.setSpacing(0)

        # A: Настройки отображения
        sec_a = QWidget(); sec_a.setObjectName("result_subsection"); sec_a.setMinimumWidth(160); sec_a.setMaximumWidth(220)
        la = QVBoxLayout(sec_a); la.setContentsMargins(12, 8, 10, 8); la.setSpacing(6)
        la.addWidget(_result_section("Отображение"))
        rb_r1 = QHBoxLayout(); rb_r1.setSpacing(4)
        self.rb_display_pv = QRadioButton("Pos. Vector"); self.rb_display_cf = QRadioButton("Coord Frame")
        self.rb_display_pv.setChecked(True)
        grp1 = QButtonGroup(sec_a); grp1.addButton(self.rb_display_pv, 0); grp1.addButton(self.rb_display_cf, 1)
        rb_r1.addWidget(self.rb_display_pv); rb_r1.addWidget(self.rb_display_cf); la.addLayout(rb_r1)
        rb_r2 = QHBoxLayout(); rb_r2.setSpacing(4)
        self.rb_dir_fwd = QRadioButton("Исх → Опорн"); self.rb_dir_inv = QRadioButton("Опорн → Исх")
        self.rb_dir_fwd.setChecked(True)
        grp2 = QButtonGroup(sec_a); grp2.addButton(self.rb_dir_fwd, 0); grp2.addButton(self.rb_dir_inv, 1)
        rb_r2.addWidget(self.rb_dir_fwd); rb_r2.addWidget(self.rb_dir_inv); la.addLayout(rb_r2)
        form_a = QFormLayout(); form_a.setSpacing(5); form_a.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.cmb_shift_units    = QComboBox(); self.cmb_shift_units.addItems(["м","мм"])
        self.cmb_rotation_units = QComboBox(); self.cmb_rotation_units.addItems(["Секунды (″)","Радианы"])
        self.cmb_scale_units    = QComboBox(); self.cmb_scale_units.addItems(["ppm","ppb","Безразм."])
        form_a.addRow("Сдвиг:",   self.cmb_shift_units)
        form_a.addRow("Поворот:", self.cmb_rotation_units)
        form_a.addRow("Масштаб:", self.cmb_scale_units)
        la.addLayout(form_a); la.addStretch(1)
        body_hbox.addWidget(sec_a); body_hbox.addWidget(_vline())

        # B: Параметры трансформации
        sec_b = QWidget(); sec_b.setObjectName("result_subsection"); sec_b.setMinimumWidth(220)
        lb = QVBoxLayout(sec_b); lb.setContentsMargins(12, 8, 10, 8); lb.setSpacing(6)
        lb.addWidget(_result_section("Параметры"))
        self.params_table = QTableWidget(7, 3); self.params_table.setObjectName("params_table")
        self.params_table.setHorizontalHeaderLabels(["", "Значение", "Ед."])
        self.params_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.params_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.params_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.params_table.verticalHeader().setVisible(False)
        self.params_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.params_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.params_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.params_table.setShowGrid(False)
        self.params_table.setToolTip("Кликните на строку — значение скопируется в буфер обмена")
        mono = QFont("Cascadia Code"); mono.setStyleHint(QFont.StyleHint.Monospace)
        for row, (p, v, u) in enumerate([("Tx","28.7427","м"),("Ty","-135.2849","м"),("Tz","-95.6312","м"),
                                          ("Rx","0.21462","″"),("Ry","-0.31847","″"),("Rz","0.15683","″"),("dS","0.84215","ppm")]):
            ip = QTableWidgetItem(p); ip.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            iv = QTableWidgetItem(v); iv.setFont(mono); iv.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            iu = QTableWidgetItem(u); iu.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.params_table.setItem(row, 0, ip); self.params_table.setItem(row, 1, iv); self.params_table.setItem(row, 2, iu)
        self.params_table.verticalHeader().setDefaultSectionSize(24)
        lb.addWidget(self.params_table, 1)
        body_hbox.addWidget(sec_b); body_hbox.addWidget(_vline())

        # C: Оценка точности
        sec_c = QWidget(); sec_c.setObjectName("result_subsection"); sec_c.setMinimumWidth(200)
        lc = QVBoxLayout(sec_c); lc.setContentsMargins(12, 8, 12, 8); lc.setSpacing(6)
        lc.addWidget(_result_section("Точность"))
        rms_row = QHBoxLayout()
        self.lbl_rms_big = QLabel("RMS: 0.016 м"); self.lbl_rms_big.setObjectName("rms_big")
        self.lbl_rms_badge = QLabel("● В ДОПУСКЕ"); self.lbl_rms_badge.setObjectName("badge_ok")
        rms_row.addWidget(self.lbl_rms_big); rms_row.addStretch(); rms_row.addWidget(self.lbl_rms_badge)
        lc.addLayout(rms_row); lc.addWidget(_hline())
        acc_grid = QGridLayout(); acc_grid.setSpacing(4); acc_grid.setColumnStretch(1, 1)
        for i, (cap, attr, default) in enumerate([("RMS X:","lbl_rms_x","—"),("RMS Y:","lbl_rms_y","—"),
                                                   ("RMS Z:","lbl_rms_z","—"),("Прост.:","lbl_rms_spatial","—"),("Макс |d|:","lbl_rms_max","—")]):
            cl = QLabel(cap); cl.setObjectName("acc_caption")
            vl = QLabel(default); vl.setObjectName("mono_value"); vl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            setattr(self, attr, vl)
            acc_grid.addWidget(cl, i, 0); acc_grid.addWidget(vl, i, 1)
        lc.addLayout(acc_grid); lc.addStretch(1)
        body_hbox.addWidget(sec_c)

        l2.addWidget(body, 1)
        self.results_splitter.addWidget(col2)

        # rb_method_pv / rb_method_cf — алиасы на виджеты отображения
        self.rb_method_pv = self.rb_display_pv
        self.rb_method_cf = self.rb_display_cf

        return panel

    # ── Статусбар ─────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        self.setStatusBar(QStatusBar())

    # ── Сплиттеры ─────────────────────────────────────────────────────────────

    def _configure_splitters(self):
        self.main_splitter.setSizes([350, 930])
        self.right_splitter.setSizes([420, 240])
        self.results_splitter.setSizes([260, 700])
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, False)