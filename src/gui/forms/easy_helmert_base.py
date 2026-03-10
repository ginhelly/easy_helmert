# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 4.2.1-0-g80c4cb6)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class BaseMainFrame
###########################################################################

class BaseMainFrame ( wx.Frame ):

    def __init__( self, parent ):
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"Easy Helmert", pos = wx.DefaultPosition, size = wx.Size( 1034,621 ), style = wx.DEFAULT_FRAME_STYLE|wx.RESIZE_BORDER|wx.SYSTEM_MENU|wx.TAB_TRAVERSAL )

        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_HIGHLIGHTTEXT ) )

        self.m_statusBar1 = self.CreateStatusBar( 1, wx.STB_SIZEGRIP, wx.ID_ANY )
        self.m_menubar1 = wx.MenuBar( 0 )
        self.m_menu1 = wx.Menu()
        self.m_menuItem11 = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Новый расчёт"+ u"\t" + u"CTRL+N", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menuItem11.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_NEW,  ) )
        self.m_menu1.Append( self.m_menuItem11 )

        self.m_menuItem1 = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Импорт координат из текстового файла..."+ u"\t" + u"CTRL+O", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menuItem1.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_FILE_OPEN,  ) )
        self.m_menu1.Append( self.m_menuItem1 )

        self.m_menuItem3 = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Импорт калибровки...", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menu1.Append( self.m_menuItem3 )

        self.m_menu1.AppendSeparator()

        self.m_menuItem2 = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Сохранить таблицу в файл..."+ u"\t" + u"CTRL+S", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menuItem2.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_FILE_SAVE,  ) )
        self.m_menu1.Append( self.m_menuItem2 )

        self.m_menuItem6 = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Сохранить калибровку...", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menu1.Append( self.m_menuItem6 )

        self.m_menuItem7 = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Сохранить WKT...", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menu1.Append( self.m_menuItem7 )

        self.m_menu1.AppendSeparator()

        self.m_exit_item = wx.MenuItem( self.m_menu1, wx.ID_EXIT, u"Выход"+ u"\t" + u"CTRL+Q", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_exit_item.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_QUIT,  ) )
        self.m_menu1.Append( self.m_exit_item )

        self.m_menubar1.Append( self.m_menu1, u"Файл" )

        self.m_menu2 = wx.Menu()
        self.m_menuItem8 = wx.MenuItem( self.m_menu2, wx.ID_ANY, u"О программе", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_menuItem8.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_HELP_PAGE,  ) )
        self.m_menu2.Append( self.m_menuItem8 )

        self.m_menubar1.Append( self.m_menu2, u"Программа" )

        self.SetMenuBar( self.m_menubar1 )

        self.m_toolbar = self.CreateToolBar( wx.TB_HORIZONTAL, wx.ID_ANY )
        self.m_toolbar.AddSeparator()

        self.m_tool11 = self.m_toolbar.AddTool( wx.ID_ANY, u"Новый расчёт", wx.ArtProvider.GetBitmap( wx.ART_NEW,  ), wx.NullBitmap, wx.ITEM_NORMAL, wx.EmptyString, u"Очистить таблицу и начать новый расчёт", None )

        self.m_tool1 = self.m_toolbar.AddTool( wx.ID_ANY, u"Импорт координат из текстового файла", wx.ArtProvider.GetBitmap( wx.ART_FILE_OPEN,  ), wx.NullBitmap, wx.ITEM_NORMAL, wx.EmptyString, u"Импорт координат из текстового файла...", None )

        self.m_tool5 = self.m_toolbar.AddTool( wx.ID_ANY, u"Импорт калибровки...", wx.ArtProvider.GetBitmap( wx.ART_ADD_BOOKMARK,  ), wx.NullBitmap, wx.ITEM_NORMAL, wx.EmptyString, u"Импорт калибровки из файла контроллера...", None )

        self.m_toolbar.AddSeparator()

        self.m_tool6 = self.m_toolbar.AddTool( wx.ID_ANY, u"Рассчитать калибровку", wx.ArtProvider.GetBitmap( wx.ART_GO_FORWARD,  ), wx.NullBitmap, wx.ITEM_NORMAL, wx.EmptyString, u"Рассчитать калибровку!", None )

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

        self.m_btn_swap_dst = wx.Button( self.m_panel_input, wx.ID_ANY, u"X↔Y цел.", wx.DefaultPosition, wx.DefaultSize, 0 )

        self.m_btn_swap_dst.SetBitmap( wx.NullBitmap )
        self.m_btn_swap_dst.SetToolTip( u"Поменять местами X и Y у точек в ЦЕЛЕВОЙ системе" )

        bSizerTableHeader.Add( self.m_btn_swap_dst, 0, wx.ALL|wx.FIXED_MINSIZE, 5 )

        self.m_staticline11 = wx.StaticLine( self.m_panel_input, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_VERTICAL )
        bSizerTableHeader.Add( self.m_staticline11, 0, wx.EXPAND |wx.ALL, 5 )

        self.m_btn_calc = wx.Button( self.m_panel_input, wx.ID_ANY, u"РАССЧИТАТЬ", wx.DefaultPosition, wx.DefaultSize, wx.BU_EXACTFIT )

        self.m_btn_calc.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_GO_FORWARD,  ) )
        self.m_btn_calc.SetMinSize( wx.Size( 150,-1 ) )

        bSizerTableHeader.Add( self.m_btn_calc, 0, wx.ALL|wx.FIXED_MINSIZE, 5 )


        bSizerInput.Add( bSizerTableHeader, 0, wx.EXPAND, 5 )

        self.m_grid_placeholder = wx.Panel( self.m_panel_input, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        bSizerInput.Add( self.m_grid_placeholder, 1, wx.EXPAND |wx.ALL, 2 )


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


        bSizerResultHeader.Add( ( 0, 0), 1, wx.EXPAND, 5 )

        self.m_btn_copy_wkt = wx.Button( self.m_panel_result, wx.ID_ANY, u"Копировать WKT", wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizerResultHeader.Add( self.m_btn_copy_wkt, 0, wx.ALL|wx.FIXED_MINSIZE, 5 )

        self.m_btn_copy_proj4 = wx.Button( self.m_panel_result, wx.ID_ANY, u"Копировать Proj4", wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizerResultHeader.Add( self.m_btn_copy_proj4, 0, wx.ALL|wx.FIXED_MINSIZE, 5 )

        self.m_btn_save_result = wx.Button( self.m_panel_result, wx.ID_ANY, u"Сохранить калибровку...", wx.DefaultPosition, wx.DefaultSize, 0 )

        self.m_btn_save_result.SetBitmap( wx.ArtProvider.GetBitmap( wx.ART_FILE_SAVE_AS,  ) )
        self.m_btn_save_result.SetMinSize( wx.Size( 150,-1 ) )

        bSizerResultHeader.Add( self.m_btn_save_result, 0, wx.ALL|wx.FIXED_MINSIZE, 5 )


        bSizerResult.Add( bSizerResultHeader, 0, wx.EXPAND, 5 )

        self.m_txt_result = wx.TextCtrl( self.m_panel_result, wx.ID_ANY, u"Результат расчёта...", wx.DefaultPosition, wx.DefaultSize, wx.HSCROLL|wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2 )
        self.m_txt_result.SetFont( wx.Font( 10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Courier" ) )
        self.m_txt_result.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_INACTIVECAPTION ) )

        bSizerResult.Add( self.m_txt_result, 1, wx.ALL|wx.EXPAND, 5 )


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


