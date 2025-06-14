#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
シンプル版メインウィンドウ - AI機能なし、基本機能特化
'''

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QMenuBar, QStatusBar, QTabWidget, QMessageBox, 
                            QPushButton, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction

from modules.customers import CustomerWidget
from modules.products import ProductWidget  
from modules.invoices import InvoiceWidget
from modules.loans import LoanWidget
from core.database import db_manager

class SimpleMainWindow(QMainWindow):
    '''シンプル版メインウィンドウクラス'''
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.create_menu_bar()
        
    def setup_ui(self):
        '''UI初期化'''
        self.setWindowTitle("業務支援システム v4.0")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        layout = QVBoxLayout(central_widget)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tab_widget)
        
        # 各モジュールのタブを追加
        self.add_modules()
        
        # ステータスバー
        self.statusBar().showMessage("業務支援システム v4.0 - 準備完了")
        
    def add_modules(self):
        '''モジュールタブを追加'''
        try:
            # 取引先管理
            customer_widget = CustomerWidget()
            self.tab_widget.addTab(customer_widget, "取引先管理")
            
            # 商品管理  
            product_widget = ProductWidget()
            self.tab_widget.addTab(product_widget, "商品管理")
            
            # 貸出管理
            loan_widget = LoanWidget()
            self.tab_widget.addTab(loan_widget, "貸出管理")
            
            # 請求書管理
            invoice_widget = InvoiceWidget()
            self.tab_widget.addTab(invoice_widget, "請求書管理")
            
        except Exception as e:
            print(f"モジュール読み込みエラー: {e}")
            
    def create_menu_bar(self):
        '''メニューバー作成'''
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル")
        
        export_action = QAction("データエクスポート", self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        exit_action = QAction("終了", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # ヘルプメニュー
        help_menu = menubar.addMenu("ヘルプ")
        
        about_action = QAction("バージョン情報", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def export_data(self):
        '''データエクスポート'''
        QMessageBox.information(self, "エクスポート", "データエクスポート機能は準備中です")
        
    def show_about(self):
        '''バージョン情報表示'''
        QMessageBox.about(self, "バージョン情報", 
                         "業務支援システム v4.0\n"
                         "安定版 - 基本機能特化\n"
                         "© 2025")
