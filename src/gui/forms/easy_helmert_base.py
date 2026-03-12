# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 4.2.1-0-g80c4cb6)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc
import wx.dataview

###########################################################################
## Class BaseMainFrame
###########################################################################

class BaseMainFrame ( wx.Frame ):

    def __init__( self, parent ):
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"Easy Helmert", pos = wx.DefaultPosition, size = wx.Size( 1034,738 ), style = wx.DEFAULT_FRAME_STYLE|wx.RESIZE_BORDER|wx.SYSTEM_MENU|wx.TAB_TRAVERSAL )

        self.SetSizeHints( wx.Size( -1,600 ), wx.DefaultSize )
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_HIGHLIGHTTEXT ) )

        self.m_statusBar1 = self.CreateStatusBar( 1, wx.STB_SIZEGRIP, wx.ID_ANY )
        self.m_menubar1 = wx.MenuBar( 0 )
        self.m_menu1 = wx.Menu()
        self.m_menuItem_new_calc = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Новый расчёт"+ u"\t" + u"CTRL+N", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menuItem_new_calc.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_NEW,  ) )
        self.m_menu1.Append( self.m_menuItem_new_calc )

        self.m_menuItem_import_txt = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Импорт координат из текстового файла..."+ u"\t" + u"CTRL+O", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menuItem_import_txt.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_FILE_OPEN,  ) )
        self.m_menu1.Append( self.m_menuItem_import_txt )

        self.m_menuItem_import_calibration = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Импорт калибровки...", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menu1.Append( self.m_menuItem_import_calibration )

        self.m_menu1.AppendSeparator()

        self.m_menuItem_save_table = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Сохранить таблицу в файл..."+ u"\t" + u"CTRL+S", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menuItem_save_table.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_FILE_SAVE,  ) )
        self.m_menu1.Append( self.m_menuItem_save_table )

        self.m_menuItem6 = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Сохранить калибровку...", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menu1.Append( self.m_menuItem6 )

        self.m_menu1.AppendSeparator()

        self.m_exit_item = wx.MenuItem( self.m_menu1, wx.ID_EXIT, u"Выход"+ u"\t" + u"CTRL+Q", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_exit_item.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_QUIT,  ) )
        self.m_menu1.Append( self.m_exit_item )

        self.m_menubar1.Append( self.m_menu1, u"Файл" )

        self.m_menu3 = wx.Menu()
        self.m_menuItem_save_wkt1 = wx.MenuItem( self.m_menu3, wx.ID_ANY, u"Сохранить как WKT...", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menu3.Append( self.m_menuItem_save_wkt1 )

        self.m_menuItem_save_wkt2 = wx.MenuItem( self.m_menu3, wx.ID_ANY, u"Сохранить как WKT2...", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menu3.Append( self.m_menuItem_save_wkt2 )

        self.m_menuItem_save_proj4 = wx.MenuItem( self.m_menu3, wx.ID_ANY, u"Сохранить как Proj4...", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menu3.Append( self.m_menuItem_save_proj4 )

        self.m_menu3.AppendSeparator()

        self.m_menuItem_copy_wkt1 = wx.MenuItem( self.m_menu3, wx.ID_ANY, u"Копировать WKT в буфер обмена", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menu3.Append( self.m_menuItem_copy_wkt1 )

        self.m_menuItem_copy_wkt2 = wx.MenuItem( self.m_menu3, wx.ID_ANY, u"Копировать WKT2 в буфер обмена", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menu3.Append( self.m_menuItem_copy_wkt2 )

        self.m_menuItem_copy_proj4 = wx.MenuItem( self.m_menu3, wx.ID_ANY, u"Копировать Proj4 в буфер обмена", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menu3.Append( self.m_menuItem_copy_proj4 )

        self.m_menubar1.Append( self.m_menu3, u"Вычисленные параметры" )

        self.m_menu2 = wx.Menu()
        self.m_menuItem8 = wx.MenuItem( self.m_menu2, wx.ID_ANY, u"О программе", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menuItem8.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_HELP_PAGE,  ) )
        self.m_menu2.Append( self.m_menuItem8 )

        self.m_menubar1.Append( self.m_menu2, u"Программа" )

        self.SetMenuBar( self.m_menubar1 )

        self.m_toolbar = self.CreateToolBar( wx.TB_HORIZONTAL, wx.ID_ANY )
        self.m_toolbar.AddSeparator()

        self.m_tool_new_calc = self.m_toolbar.AddTool( wx.ID_ANY, u"Новый расчёт", wx.ArtProvider.GetBitmap( wx.ART_NEW,  ), wx.NullBitmap, wx.ITEM_NORMAL, wx.EmptyString, u"Очистить таблицу и начать новый расчёт", None )

        self.m_tool_import_txt = self.m_toolbar.AddTool( wx.ID_ANY, u"Импорт координат из текстового файла", wx.ArtProvider.GetBitmap( wx.ART_FILE_OPEN,  ), wx.NullBitmap, wx.ITEM_NORMAL, wx.EmptyString, u"Импорт координат из текстового файла...", None )

        self.m_tool_import_calibration = self.m_toolbar.AddTool( wx.ID_ANY, u"Импорт калибровки...", wx.ArtProvider.GetBitmap( wx.ART_ADD_BOOKMARK,  ), wx.NullBitmap, wx.ITEM_NORMAL, wx.EmptyString, u"Импорт калибровки из файла контроллера...", None )

        self.m_toolbar.AddSeparator()

        self.m_tool_calculate = self.m_toolbar.AddTool( wx.ID_ANY, u"Рассчитать калибровку", wx.ArtProvider.GetBitmap( wx.ART_GO_FORWARD,  ), wx.NullBitmap, wx.ITEM_NORMAL, wx.EmptyString, u"Рассчитать калибровку!", None )

        self.m_toolbar.AddSeparator()

        self.m_toolbar.Realize()

        bSizer2 = wx.BoxSizer( wx.VERTICAL )

        self.m_splitter = wx.SplitterWindow( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.SP_3D|wx.SP_LIVE_UPDATE )
        self.m_splitter.SetSashGravity( 0.65 )
        self.m_splitter.Bind( wx.EVT_IDLE, self.m_splitterOnIdle )
        self.m_splitter.SetMinimumPaneSize( 150 )

        self.m_panel_input = wx.Panel( self.m_splitter, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        bSizerInput = wx.BoxSizer( wx.VERTICAL )

        bSizerTableHeader = wx.BoxSizer( wx.HORIZONTAL )

        self.m_lbl_table = wx.StaticText( self.m_panel_input, wx.ID_ANY, u"Точки калибровки", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_lbl_table.Wrap( -1 )

        self.m_lbl_table.SetFont( wx.Font( wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString ) )

        bSizerTableHeader.Add( self.m_lbl_table, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )


        bSizerTableHeader.Add( ( 0, 0), 1, wx.EXPAND, 5 )

        self.m_btn_add_row = wx.Button( self.m_panel_input, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )

        self.m_btn_add_row.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_PLUS,  ) )
        self.m_btn_add_row.SetToolTip( u"Добавить строку" )

        bSizerTableHeader.Add( self.m_btn_add_row, 0, wx.ALL|wx.FIXED_MINSIZE, 5 )

        self.m_btn_del_row = wx.Button( self.m_panel_input, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )

        self.m_btn_del_row.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_MINUS,  ) )
        self.m_btn_del_row.SetToolTip( u"Удалить строку" )

        bSizerTableHeader.Add( self.m_btn_del_row, 0, wx.ALL|wx.FIXED_MINSIZE, 5 )

        self.m_staticline1 = wx.StaticLine( self.m_panel_input, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_VERTICAL )
        bSizerTableHeader.Add( self.m_staticline1, 0, wx.EXPAND |wx.ALL, 5 )

        self.m_btn_swap_src = wx.Button( self.m_panel_input, wx.ID_ANY, u"X↔Y исх.", wx.DefaultPosition, wx.DefaultSize, 0 )

        self.m_btn_swap_src.SetBitmap( wx.NullBitmap )
        self.m_btn_swap_src.SetToolTip( u"Поменять местами X и Y у точек в ИСХОДНОЙ системе" )

        bSizerTableHeader.Add( self.m_btn_swap_src, 0, wx.ALL|wx.FIXED_MINSIZE, 5 )

        self.m_btn_swap_dst = wx.Button( self.m_panel_input, wx.ID_ANY, u"X↔Y опорн.", wx.DefaultPosition, wx.DefaultSize, 0 )

        self.m_btn_swap_dst.SetBitmap( wx.NullBitmap )
        self.m_btn_swap_dst.SetToolTip( u"Поменять местами X и Y у точек в ЦЕЛЕВОЙ системе" )

        bSizerTableHeader.Add( self.m_btn_swap_dst, 0, wx.ALL|wx.FIXED_MINSIZE, 5 )


        bSizerInput.Add( bSizerTableHeader, 0, wx.EXPAND, 5 )

        bSizerGrid = wx.BoxSizer( wx.HORIZONTAL )

        bSizerGridSettings = wx.BoxSizer( wx.VERTICAL )

        bSizerGridSettings.SetMinSize( wx.Size( 250,250 ) )
        self.m_staticText151 = wx.StaticText( self.m_panel_input, wx.ID_ANY, u"Настройки входных данных", wx.DefaultPosition, wx.Size( 320,-1 ), 0 )
        self.m_staticText151.Wrap( -1 )

        bSizerGridSettings.Add( self.m_staticText151, 0, wx.ALL, 5 )

        sbSizer3 = wx.StaticBoxSizer( wx.StaticBox( self.m_panel_input, wx.ID_ANY, u"Подгоняемая система координат" ), wx.HORIZONTAL )

        self.m_lbl_src_crs = wx.StaticText( sbSizer3.GetStaticBox(), wx.ID_ANY, u"Не выбрана", wx.DefaultPosition, wx.Size( 250,-1 ), wx.ST_ELLIPSIZE_MIDDLE )
        self.m_lbl_src_crs.Wrap( -1 )

        self.m_lbl_src_crs.SetFont( wx.Font( wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString ) )

        sbSizer3.Add( self.m_lbl_src_crs, 1, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.m_btn_set_src_crs = wx.Button( sbSizer3.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 32,-1 ), 0 )

        self.m_btn_set_src_crs.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_FIND,  ) )
        sbSizer3.Add( self.m_btn_set_src_crs, 0, wx.ALIGN_CENTER, 5 )


        bSizerGridSettings.Add( sbSizer3, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5 )

        sbSizer31 = wx.StaticBoxSizer( wx.StaticBox( self.m_panel_input, wx.ID_ANY, u"Опорная система координат" ), wx.HORIZONTAL )

        self.m_lbl_tgt_crs = wx.StaticText( sbSizer31.GetStaticBox(), wx.ID_ANY, u"Не выбрана", wx.DefaultPosition, wx.Size( 250,-1 ), wx.ST_ELLIPSIZE_MIDDLE )
        self.m_lbl_tgt_crs.Wrap( -1 )

        self.m_lbl_tgt_crs.SetFont( wx.Font( wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString ) )

        sbSizer31.Add( self.m_lbl_tgt_crs, 1, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.m_btn_set_tgt_crs = wx.Button( sbSizer31.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 32,-1 ), 0 )

        self.m_btn_set_tgt_crs.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_FIND,  ) )
        sbSizer31.Add( self.m_btn_set_tgt_crs, 0, wx.ALIGN_CENTER, 5 )


        bSizerGridSettings.Add( sbSizer31, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5 )

        bSizer27 = wx.BoxSizer( wx.HORIZONTAL )

        self.m_staticText21 = wx.StaticText( self.m_panel_input, wx.ID_ANY, u"Подсв. красным невязки >", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText21.Wrap( -1 )

        bSizer27.Add( self.m_staticText21, 0, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.m_spin_bad_threshold = wx.SpinCtrlDouble( self.m_panel_input, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 0, 100, 0.1, 1 )
        self.m_spin_bad_threshold.SetDigits( 2 )
        bSizer27.Add( self.m_spin_bad_threshold, 0, wx.ALL, 5 )

        m_choice_bad_unitsChoices = [ u"СКО", u"метров" ]
        self.m_choice_bad_units = wx.Choice( self.m_panel_input, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, m_choice_bad_unitsChoices, 0 )
        self.m_choice_bad_units.SetSelection( 1 )
        bSizer27.Add( self.m_choice_bad_units, 1, wx.ALL, 5 )


        bSizerGridSettings.Add( bSizer27, 0, wx.EXPAND, 5 )


        bSizerGridSettings.Add( ( 0, 0), 1, wx.EXPAND, 5 )

        self.m_btn_calc = wx.Button( self.m_panel_input, wx.ID_ANY, u"РАССЧИТАТЬ", wx.DefaultPosition, wx.Size( 150,-1 ), wx.BU_EXACTFIT )

        self.m_btn_calc.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_GO_FORWARD,  ) )
        self.m_btn_calc.SetMinSize( wx.Size( 150,-1 ) )

        bSizerGridSettings.Add( self.m_btn_calc, 0, wx.ALL|wx.FIXED_MINSIZE|wx.EXPAND, 5 )


        bSizerGrid.Add( bSizerGridSettings, 0, wx.EXPAND, 5 )

        self.m_grid_placeholder = wx.Panel( self.m_panel_input, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        bSizerGrid.Add( self.m_grid_placeholder, 1, wx.EXPAND |wx.ALL, 2 )


        bSizerInput.Add( bSizerGrid, 1, wx.EXPAND, 5 )


        self.m_panel_input.SetSizer( bSizerInput )
        self.m_panel_input.Layout()
        bSizerInput.Fit( self.m_panel_input )
        self.m_panel_result = wx.Panel( self.m_splitter, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        bSizerResult = wx.BoxSizer( wx.VERTICAL )

        bSizerResultHeader = wx.BoxSizer( wx.HORIZONTAL )

        self.m_lbl_result = wx.StaticText( self.m_panel_result, wx.ID_ANY, u"Параметры преобразования", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_lbl_result.Wrap( -1 )

        self.m_lbl_result.SetFont( wx.Font( wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString ) )

        bSizerResultHeader.Add( self.m_lbl_result, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )


        bSizerResult.Add( bSizerResultHeader, 0, wx.EXPAND, 5 )

        bSizer15 = wx.BoxSizer( wx.HORIZONTAL )

        bSizer17 = wx.BoxSizer( wx.VERTICAL )

        bSizer17.SetMinSize( wx.Size( 250,250 ) )
        self.m_staticText15 = wx.StaticText( self.m_panel_result, wx.ID_ANY, u"Настройки вывода параметров", wx.DefaultPosition, wx.Size( 320,-1 ), 0 )
        self.m_staticText15.Wrap( -1 )

        bSizer17.Add( self.m_staticText15, 0, wx.ALL, 5 )

        m_rb_methodChoices = [ u"EPSG:1033 (9606) Position Vector Transformation", u"EPSG:1032 (9607) Coordinate Frame Rotation" ]
        self.m_rb_method = wx.RadioBox( self.m_panel_result, wx.ID_ANY, u"Метод преобразования", wx.DefaultPosition, wx.DefaultSize, m_rb_methodChoices, 1, wx.RA_SPECIFY_COLS )
        self.m_rb_method.SetSelection( 0 )
        self.m_rb_method.SetToolTip( u"EPSG:1033 (9606) Position Vector Transformation - дефолтный для WKT- и Proj4-описаний.\nEPSG:1032 (9607) Coordinate Frame Rotation - метод, описанный в ГОСТ 32453-2017\n\nЧтобы понять, какой метод используется в вашей программе, посмотрите в ней на дефолтные 7 параметров для МСК:\nа) Если в них число 23.57 противоположно по знаку всем другим числам, то это 1032 (9607) Coordinate Frame Rotation\nб) Если в них число 23.57 по знаку совпадает с параметрами разворота (0.35 и 0.79), то это 1033 (9606) Position Vector Transformation" )

        bSizer17.Add( self.m_rb_method, 0, wx.ALL|wx.EXPAND, 5 )

        m_rb_directionChoices = [ u"Из исходной -> в опорную", u"Из опорной -> в исходную" ]
        self.m_rb_direction = wx.RadioBox( self.m_panel_result, wx.ID_ANY, u"Направление параметров", wx.DefaultPosition, wx.DefaultSize, m_rb_directionChoices, 1, wx.RA_SPECIFY_COLS )
        self.m_rb_direction.SetSelection( 0 )
        bSizer17.Add( self.m_rb_direction, 0, wx.ALL|wx.EXPAND, 5 )

        bSizer18 = wx.BoxSizer( wx.HORIZONTAL )

        bSizer18.SetMinSize( wx.Size( -1,30 ) )
        self.m_staticText12 = wx.StaticText( self.m_panel_result, wx.ID_ANY, u"Единицы поворота", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText12.Wrap( -1 )

        bSizer18.Add( self.m_staticText12, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )

        m_choice_rotation_unitsChoices = [ u"Секунды (″)", u"Радианы" ]
        self.m_choice_rotation_units = wx.Choice( self.m_panel_result, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, m_choice_rotation_unitsChoices, 0 )
        self.m_choice_rotation_units.SetSelection( 0 )
        bSizer18.Add( self.m_choice_rotation_units, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )


        bSizer17.Add( bSizer18, 0, wx.EXPAND, 5 )

        bSizer181 = wx.BoxSizer( wx.HORIZONTAL )

        bSizer181.SetMinSize( wx.Size( -1,30 ) )
        self.m_staticText121 = wx.StaticText( self.m_panel_result, wx.ID_ANY, u"Единицы масштаба", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText121.Wrap( -1 )

        bSizer181.Add( self.m_staticText121, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )

        m_choice_scale_unitsChoices = [ u"Безразмерный коэффициент", u"Миллионные части (ppm)", u"Миллиардные части (ppb)" ]
        self.m_choice_scale_units = wx.Choice( self.m_panel_result, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, m_choice_scale_unitsChoices, 0 )
        self.m_choice_scale_units.SetSelection( 1 )
        bSizer181.Add( self.m_choice_scale_units, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )


        bSizer17.Add( bSizer181, 0, wx.EXPAND, 5 )


        bSizer15.Add( bSizer17, 0, wx.EXPAND, 5 )

        self.m_txt_result = wx.TextCtrl( self.m_panel_result, wx.ID_ANY, u"Результат расчёта...", wx.DefaultPosition, wx.DefaultSize, wx.HSCROLL|wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2|wx.BORDER_THEME )
        self.m_txt_result.SetFont( wx.Font( 10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString ) )
        self.m_txt_result.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_INACTIVEBORDER ) )

        bSizer15.Add( self.m_txt_result, 1, wx.ALL|wx.EXPAND, 5 )


        bSizerResult.Add( bSizer15, 1, wx.EXPAND, 5 )


        self.m_panel_result.SetSizer( bSizerResult )
        self.m_panel_result.Layout()
        bSizerResult.Fit( self.m_panel_result )
        self.m_splitter.SplitHorizontally( self.m_panel_input, self.m_panel_result, 0 )
        bSizer2.Add( self.m_splitter, 1, wx.ALL|wx.EXPAND, 5 )


        self.SetSizer( bSizer2 )
        self.Layout()

        self.Centre( wx.BOTH )

        # Connect Events
        self.Bind( wx.EVT_MENU, self.on_exit, id = self.m_exit_item.GetId() )

    def __del__( self ):
        pass


    # Virtual event handlers, override them in your derived class
    def on_exit( self, event ):
        event.Skip()

    def m_splitterOnIdle( self, event ):
        self.m_splitter.SetSashPosition( 0 )
        self.m_splitter.Unbind( wx.EVT_IDLE )

    # Virtual image path resolution method. Override this in your derived class.
    def get_resource_path( self, bitmap_path ):
        return bitmap_path


###########################################################################
## Class BaseCRSPickerDialog
###########################################################################

class BaseCRSPickerDialog ( wx.Dialog ):

    def __init__( self, parent ):
        wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Выбрать систему координат", pos = wx.DefaultPosition, size = wx.Size( 860,640 ), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER )

        self.SetSizeHints( wx.Size( 640,480 ), wx.DefaultSize )

        m_root_sizer = wx.BoxSizer( wx.VERTICAL )

        self.m_notebook1 = wx.Notebook( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_page_search = wx.Panel( self.m_notebook1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        bSizerSearch = wx.BoxSizer( wx.VERTICAL )

        bSizerSearchTop = wx.BoxSizer( wx.HORIZONTAL )

        self.m_txt_search = wx.TextCtrl( self.m_page_search, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizerSearchTop.Add( self.m_txt_search, 1, wx.ALL|wx.EXPAND, 5 )

        self.m_chk_projected = wx.CheckBox( self.m_page_search, wx.ID_ANY, u"Проецированные", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_chk_projected.SetValue(True)
        bSizerSearchTop.Add( self.m_chk_projected, 0, wx.ALIGN_CENTER|wx.ALL, 5 )

        self.m_chk_geographic = wx.CheckBox( self.m_page_search, wx.ID_ANY, u"Географические", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_chk_geographic.SetValue(True)
        bSizerSearchTop.Add( self.m_chk_geographic, 0, wx.ALIGN_CENTER|wx.ALL, 5 )


        bSizerSearch.Add( bSizerSearchTop, 0, wx.EXPAND, 5 )

        self.m_tree_search = wx.dataview.DataViewTreeCtrl( self.m_page_search, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.dataview.DV_NO_HEADER|wx.dataview.DV_ROW_LINES )
        bSizerSearch.Add( self.m_tree_search, 1, wx.ALL|wx.EXPAND, 5 )


        self.m_page_search.SetSizer( bSizerSearch )
        self.m_page_search.Layout()
        bSizerSearch.Fit( self.m_page_search )
        self.m_notebook1.AddPage( self.m_page_search, u"Поиск по базе", False )
        self.m_page_custom = wx.Panel( self.m_notebook1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        bSizerCustom = wx.BoxSizer( wx.VERTICAL )

        self.m_lbl_custom_hint = wx.StaticText( self.m_page_custom, wx.ID_ANY, u"Вставьте строку формата WKT или Proj4:", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_lbl_custom_hint.Wrap( -1 )

        bSizerCustom.Add( self.m_lbl_custom_hint, 0, wx.ALL, 5 )

        self.m_txt_wkt_input = wx.TextCtrl( self.m_page_custom, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.TE_MULTILINE )
        self.m_txt_wkt_input.SetMinSize( wx.Size( -1,150 ) )

        bSizerCustom.Add( self.m_txt_wkt_input, 1, wx.ALL|wx.EXPAND, 5 )

        bSizer22 = wx.BoxSizer( wx.HORIZONTAL )

        self.m_btn_parse_crs = wx.Button( self.m_page_custom, wx.ID_ANY, u"Импортировать из строки", wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizer22.Add( self.m_btn_parse_crs, 0, wx.ALL, 5 )

        self.m_btn_import_crs_from_file = wx.Button( self.m_page_custom, wx.ID_ANY, u"Импортировать из файла...", wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizer22.Add( self.m_btn_import_crs_from_file, 0, wx.ALL, 5 )


        bSizerCustom.Add( bSizer22, 0, wx.EXPAND, 5 )


        self.m_page_custom.SetSizer( bSizerCustom )
        self.m_page_custom.Layout()
        bSizerCustom.Fit( self.m_page_custom )
        self.m_notebook1.AddPage( self.m_page_custom, u"Импорт из WKT / Proj4", False )

        m_root_sizer.Add( self.m_notebook1, 1, wx.EXPAND |wx.ALL, 5 )

        m_staticbox_info = wx.StaticBoxSizer( wx.StaticBox( self, wx.ID_ANY, u"Параметры выбранной системы координат" ), wx.VERTICAL )

        self.m_txt_crs_info = wx.TextCtrl( m_staticbox_info.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2 )
        self.m_txt_crs_info.SetFont( wx.Font( wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString ) )
        self.m_txt_crs_info.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_INACTIVEBORDER ) )
        self.m_txt_crs_info.SetMinSize( wx.Size( -1,160 ) )

        m_staticbox_info.Add( self.m_txt_crs_info, 1, wx.ALL|wx.EXPAND, 5 )


        m_root_sizer.Add( m_staticbox_info, 1, wx.ALL|wx.EXPAND, 5 )

        m_btn_sizer = wx.BoxSizer( wx.HORIZONTAL )


        m_btn_sizer.Add( ( 0, 0), 1, wx.EXPAND, 5 )

        self.m_btn_ok = wx.Button( self, wx.ID_OK, u"Выбрать", wx.DefaultPosition, wx.DefaultSize, 0 )
        m_btn_sizer.Add( self.m_btn_ok, 0, wx.ALL, 5 )

        self.m_btn_cancel = wx.Button( self, wx.ID_CANCEL, u"Отмена", wx.DefaultPosition, wx.DefaultSize, 0 )
        m_btn_sizer.Add( self.m_btn_cancel, 0, wx.ALL, 5 )


        m_root_sizer.Add( m_btn_sizer, 0, wx.EXPAND, 5 )


        self.SetSizer( m_root_sizer )
        self.Layout()

        self.Centre( wx.BOTH )

    def __del__( self ):
        pass

    # Virtual image path resolution method. Override this in your derived class.
    def get_resource_path( self, bitmap_path ):
        return bitmap_path


