"""
メインウィンドウクラス - AI統合・アクセシビリティ対応版
モダンなデザインのメインウィンドウ
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QMenuBar, QStatusBar, QAction, QToolBar, QSplitter,
                            QDockWidget, QTabWidget, QMessageBox, QPushButton,
                            QLabel, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QKeySequence, QIcon, QFont, QAction as QGuiAction
from typing import Dict, Any, Optional

from .dashboard import Dashboard
from .components.base_widget import BaseWidget
from .plugin_manager_dialog import PluginManagerDialog
from ..core.config_manager import config_manager
from ..core.database import db_manager
from ..core.plugin_manager import PluginManager
from ..core.ai_integration import ai_assistant, AICommandWidget, AISettingsDialog
from ..core.accessibility import accessibility_manager, AccessibilityDialog
from ..modules.customers import CustomerWidget
from ..modules.products import ProductWidget
from ..modules.invoices import InvoiceWidget
from ..modules.loans import LoanWidget
from ..modules.analytics import AnalyticsWidget


class MainWindow(QMainWindow):
    """メインウィンドウクラス"""
    
    # シグナル定義
    module_requested = pyqtSignal(str)  # モジュール名
    
    def __init__(self):
        super().__init__()
        
        # 初期化
        self._current_module = None
        self._modules = {}
        self._dock_widgets = {}
        
        # プラグインマネージャー初期化
        self.plugin_manager = PluginManager(self)
        
        # アクセシビリティ適用
        accessibility_manager.apply_font_to_application()
        accessibility_manager.apply_high_contrast()
        
        # UI構築
        self.setup_ui()
        self.create_menu_bar()
        self.create_tool_bar()
        self.create_status_bar()
        self.setup_shortcuts()
        self.load_theme()
        
        # AI・アクセシビリティ機能追加
        self.setup_ai_features()
        
        # 初期表示
        self.show_dashboard()
        
        # シグナル接続
        self.setup_signals()
        
        # 音声ガイド
        accessibility_manager.speak("業務支援システムが起動しました")
        
        print("メインウィンドウを初期化しました")
    
    def setup_ui(self):
        """UI初期化"""
        # ウィンドウ設定
        self.setWindowTitle(config_manager.get("app.name", "業務支援システム v3.0"))
        self.setMinimumSize(1200, 800)
        
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # スプリッター（サイドバーとメインエリア）
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # サイドバー
        self.create_sidebar()
        
        # メインエリア
        self.main_area = QTabWidget()
        self.main_area.setTabsClosable(True)
        self.main_area.tabCloseRequested.connect(self.close_tab)
        self.splitter.addWidget(self.main_area)
        
        # スプリッター比率設定
        self.splitter.setSizes([250, 1150])
        self.splitter.setCollapsible(0, True)
    
    def create_sidebar(self):
        """サイドバー作成"""
        self.sidebar = QFrame()
        self.sidebar.setMaximumWidth(300)
        self.sidebar.setMinimumWidth(200)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        # ロゴ・タイトル部分
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        
        app_title = QLabel(config_manager.get("app.name"))
        app_title.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(app_title)
        
        sidebar_layout.addWidget(header_frame)
        
        # ナビゲーションメニュー
        self.create_navigation_menu(sidebar_layout)
        
        # 統計情報エリア
        self.create_stats_area(sidebar_layout)
        
        sidebar_layout.addStretch()
        self.splitter.addWidget(self.sidebar)
    
    def create_navigation_menu(self, layout):
        """ナビゲーションメニュー作成"""
        nav_frame = QFrame()
        nav_layout = QVBoxLayout(nav_frame)
        
        # メニューアイテム定義
        menu_items = [
            ("🏠", "ダッシュボード", self.show_dashboard),
            ("👥", "取引先管理", lambda: self.open_module("customers")),
            ("📦", "商品管理", lambda: self.open_module("products")),
            ("📊", "在庫管理", lambda: self.open_module("inventory")),
            ("🛠", "貸出処理", lambda: self.open_module("loans")),
            ("📄", "請求書作成", lambda: self.open_module("invoices")),
            ("🔍", "履歴検索", lambda: self.open_module("search")),
            ("📈", "売上集計", lambda: self.open_module("analytics")),
            ("🤖", "AI音声コマンド", lambda: self.open_module("ai_commands")),
            ("♿", "アクセシビリティ", lambda: self.open_module("accessibility")),
            ("⚙️", "システム設定", lambda: self.open_module("settings"))
        ]
        
        for icon, text, callback in menu_items:
            btn = self.create_nav_button(icon, text, callback)
            nav_layout.addWidget(btn)
        
        layout.addWidget(nav_frame)
    
    def create_nav_button(self, icon: str, text: str, callback) -> QPushButton:
        """ナビゲーションボタン作成"""
        button = QPushButton(f"{icon} {text}")
        
        # ボタンクリック時に音声ガイド
        def wrapped_callback():
            accessibility_manager.speak(f"{text}を開いています")
            callback()
        
        button.clicked.connect(wrapped_callback)
        
        # アクセシビリティスタイル適用
        button_style = accessibility_manager.get_large_button_style() + """
            QPushButton {
                text-align: left;
                padding: 12px 16px;
                border: none;
                border-radius: 4px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(33, 150, 243, 0.2);
            }
        """
        button.setStyleSheet(button_style)
        return button
    
    def create_stats_area(self, layout):
        """統計情報エリア作成"""
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(33, 150, 243, 0.05);
                border-radius: 8px;
                padding: 16px;
                margin: 8px;
            }
        """)
        
        stats_layout = QVBoxLayout(stats_frame)
        
        # タイトル
        title = QLabel("📊 システム状況")
        title.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        stats_layout.addWidget(title)
        
        # 統計ラベル
        self.stats_labels = {
            "customers": QLabel("取引先: -"),
            "products": QLabel("商品: -"),
            "active_loans": QLabel("貸出中: -"),
            "pending_invoices": QLabel("未入金: -")
        }
        
        for label in self.stats_labels.values():
            label.setStyleSheet("color: #555; font-size: 11px; margin: 2px;")
            stats_layout.addWidget(label)
        
        layout.addWidget(stats_frame)
        
        # 統計更新タイマー
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(30000)  # 30秒間隔
        self.update_stats()  # 初回更新
    
    def create_menu_bar(self):
        """メニューバー作成"""
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル(&F)")
        
        # 新規作成
        new_action = QAction("新規作成(&N)", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        # インポート/エクスポート
        import_action = QAction("インポート(&I)...", self)
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        
        export_action = QAction("エクスポート(&E)...", self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # 印刷
        print_action = QAction("印刷(&P)", self)
        print_action.setShortcut(QKeySequence.StandardKey.Print)
        print_action.triggered.connect(self.print_document)
        file_menu.addAction(print_action)
        
        file_menu.addSeparator()
        
        # 終了
        exit_action = QAction("終了(&X)", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 編集メニュー
        edit_menu = menubar.addMenu("編集(&E)")
        
        undo_action = QAction("元に戻す(&U)", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("やり直し(&R)", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        find_action = QAction("検索(&F)...", self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self.show_search)
        edit_menu.addAction(find_action)
        
        # 表示メニュー
        view_menu = menubar.addMenu("表示(&V)")
        
        dashboard_action = QAction("ダッシュボード(&D)", self)
        dashboard_action.setShortcut(QKeySequence("Ctrl+D"))
        dashboard_action.triggered.connect(self.show_dashboard)
        view_menu.addAction(dashboard_action)
        
        view_menu.addSeparator()
        
        # テーマ切り替え
        theme_action = QAction("ダークテーマ切り替え(&T)", self)
        theme_action.setShortcut(QKeySequence("Ctrl+T"))
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)
        
        # ツールメニュー
        tools_menu = menubar.addMenu("ツール(&T)")
        
        backup_action = QAction("バックアップ作成(&B)", self)
        backup_action.triggered.connect(self.create_backup)
        tools_menu.addAction(backup_action)
        
        optimize_action = QAction("データベース最適化(&O)", self)
        optimize_action.triggered.connect(self.optimize_database)
        tools_menu.addAction(optimize_action)
        
        tools_menu.addSeparator()
        
        # AI設定
        ai_settings_action = QAction("AI機能設定(&A)...", self)
        ai_settings_action.triggered.connect(self.show_ai_settings)
        tools_menu.addAction(ai_settings_action)
        
        # アクセシビリティ設定
        accessibility_action = QAction("アクセシビリティ設定(&C)...", self)
        accessibility_action.triggered.connect(self.show_accessibility_settings)
        tools_menu.addAction(accessibility_action)
        
        tools_menu.addSeparator()
        
        settings_action = QAction("設定(&S)...", self)
        settings_action.setShortcut(QKeySequence.StandardKey.Preferences)
        settings_action.triggered.connect(lambda: self.open_module("settings"))
        tools_menu.addAction(settings_action)
        
        # ヘルプメニュー
        help_menu = menubar.addMenu("ヘルプ(&H)")
        
        manual_action = QAction("使い方(&U)", self)
        manual_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        manual_action.triggered.connect(self.show_help)
        help_menu.addAction(manual_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("このアプリケーションについて(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_tool_bar(self):
        """ツールバー作成"""
        toolbar = QToolBar("メインツールバー")
        toolbar.setMovable(False)
        
        # よく使う機能のボタン
        actions = [
            ("🏠", "ダッシュボード", self.show_dashboard),
            ("➕", "新規作成", self.new_file),
            ("🔍", "検索", self.show_search),
            ("💾", "バックアップ", self.create_backup),
            ("⚙️", "設定", lambda: self.open_module("settings"))
        ]
        
        for icon, tooltip, callback in actions:
            action = QAction(icon, self)
            action.setToolTip(tooltip)
            action.triggered.connect(callback)
            toolbar.addAction(action)
            
            if tooltip == "検索":
                toolbar.addSeparator()
        
        self.addToolBar(toolbar)
    
    def create_status_bar(self):
        """ステータスバー作成"""
        status_bar = QStatusBar()
        
        # メッセージエリア
        self.status_message = QLabel("準備完了")
        status_bar.addWidget(self.status_message)
        
        # 右側に統計情報
        status_bar.addPermanentWidget(QLabel("|"))
        
        self.status_db = QLabel("DB: 接続中")
        status_bar.addPermanentWidget(self.status_db)
        
        self.setStatusBar(status_bar)
    
    def setup_shortcuts(self):
        """ショートカットキー設定"""
        # モジュール切り替えショートカット
        shortcuts = {
            "Ctrl+1": lambda: self.open_module("customers"),
            "Ctrl+2": lambda: self.open_module("products"),
            "Ctrl+3": lambda: self.open_module("inventory"),
            "Ctrl+4": lambda: self.open_module("loans"),
            "Ctrl+5": lambda: self.open_module("invoices"),
            "Ctrl+6": lambda: self.open_module("search"),
            "Ctrl+7": lambda: self.open_module("analytics"),
            "Ctrl+8": lambda: self.open_module("ai_commands"),
            "Ctrl+9": lambda: self.open_module("accessibility"),
            "F5": self.refresh_current,
            "Escape": self.close_current_tab
        }
        
        for key, callback in shortcuts.items():
            action = QAction(self)
            action.setShortcut(QKeySequence(key))
            action.triggered.connect(callback)
            self.addAction(action)
    
    def load_theme(self):
        """テーマを読み込み"""
        stylesheet = config_manager.get_stylesheet()
        self.setStyleSheet(stylesheet)
    
    def setup_signals(self):
        """シグナル接続"""
        # 設定変更
        config_manager.theme_changed.connect(self.update_theme)
        
        # データベースイベント
        db_manager.data_changed.connect(self.on_data_changed)
        db_manager.error_occurred.connect(self.show_error)
    
    def setup_ai_features(self):
        """AI機能セットアップ"""
        try:
            # AI音声コマンドウィジェットを作成してドックに追加
            self.ai_command_widget = AICommandWidget(ai_assistant)
            ai_dock = QDockWidget("AI音声コマンド", self)
            ai_dock.setWidget(self.ai_command_widget)
            ai_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, ai_dock)
            
            # AI コマンド処理接続
            self.ai_command_widget.command_recognized.connect(self.handle_ai_command)
            
        except Exception as e:
            print(f"AI機能セットアップエラー: {e}")
    
    def handle_ai_command(self, action: str, parameters: dict):
        """AIコマンド処理"""
        try:
            if action == "search_customer":
                self.open_module("customers")
                accessibility_manager.speak("取引先管理を開きました")
            elif action == "search_product":
                self.open_module("products")
                accessibility_manager.speak("商品管理を開きました")
            elif action == "create_loan":
                self.open_module("loans")
                accessibility_manager.speak("貸出処理を開きました")
            elif action == "create_invoice":
                self.open_module("invoices")
                accessibility_manager.speak("請求書作成を開きました")
            elif action == "analyze_sales":
                self.open_module("analytics")
                accessibility_manager.speak("売上分析を開きました")
            elif action == "check_inventory":
                self.open_module("inventory")
                accessibility_manager.speak("在庫管理を開きました")
            elif action == "text_response":
                text = parameters.get("text", "")
                accessibility_manager.speak(text)
            else:
                accessibility_manager.speak("コマンドを認識できませんでした")
                
        except Exception as e:
            print(f"AIコマンド処理エラー: {e}")
            accessibility_manager.speak("エラーが発生しました")
    
    def show_dashboard(self):
        """ダッシュボードを表示"""
        # 既存のダッシュボードタブを探す
        for i in range(self.main_area.count()):
            if self.main_area.tabText(i) == "🏠 ダッシュボード":
                self.main_area.setCurrentIndex(i)
                return
        
        # 新しいダッシュボードタブを作成
        dashboard = Dashboard()
        index = self.main_area.addTab(dashboard, "🏠 ダッシュボード")
        self.main_area.setCurrentIndex(index)
        
        # ダッシュボードタブは閉じられないようにする
        tab_bar = self.main_area.tabBar()
        tab_bar.setTabButton(index, tab_bar.ButtonPosition.RightSide, None)
    
    def open_module(self, module_name: str):
        """モジュールを開く"""
        print(f"モジュールを開きます: {module_name}")
        
        # タブが既に開いているかチェック
        module_names = {
            "customers": "👥 取引先管理",
            "products": "📦 商品管理",
            "inventory": "📊 在庫管理",
            "loans": "🛠 貸出処理",
            "invoices": "📄 請求書作成",
            "search": "🔍 履歴検索",
            "analytics": "📈 売上集計",
            "ai_commands": "🤖 AI音声コマンド",
            "accessibility": "♿ アクセシビリティ",
            "settings": "⚙️ システム設定"
        }
        
        tab_name = module_names.get(module_name, module_name)
        
        for i in range(self.main_area.count()):
            if self.main_area.tabText(i) == tab_name:
                self.main_area.setCurrentIndex(i)
                return
        
        # モジュール作成
        widget = self.create_module_widget(module_name)
        if widget is None:
            placeholder = QLabel(f"{module_name} モジュール\n\n実装中...")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("font-size: 18px; color: #666;")
            widget = placeholder
        
        index = self.main_area.addTab(widget, tab_name)
        self.main_area.setCurrentIndex(index)
        
        self.module_requested.emit(module_name)
    
    def create_module_widget(self, module_name: str):
        """モジュールウィジェット作成"""
        try:
            if module_name == "customers":
                return CustomerWidget()
            elif module_name == "products":
                return ProductWidget()
            elif module_name == "loans":
                return LoanWidget()
            elif module_name == "invoices":
                return InvoiceWidget()
            elif module_name == "analytics":
                return AnalyticsWidget()
            elif module_name == "ai_commands":
                # AI音声コマンド専用画面
                return AICommandWidget(ai_assistant)
            elif module_name == "accessibility":
                # アクセシビリティ設定画面
                accessibility_widget = QWidget()
                layout = QVBoxLayout(accessibility_widget)
                
                title = QLabel("アクセシビリティ設定")
                title.setFont(QFont("Yu Gothic UI", 18, QFont.Weight.Bold))
                layout.addWidget(title)
                
                settings_btn = QPushButton("設定を開く")
                settings_btn.clicked.connect(self.show_accessibility_settings)
                settings_btn.setStyleSheet(accessibility_manager.get_large_button_style())
                layout.addWidget(settings_btn)
                
                layout.addStretch()
                return accessibility_widget
            else:
                return None
        except Exception as e:
            print(f"モジュール作成エラー ({module_name}): {e}")
            return None
    
    def close_tab(self, index: int):
        """タブを閉じる"""
        if self.main_area.tabText(index) != "🏠 ダッシュボード":
            self.main_area.removeTab(index)
    
    def close_current_tab(self):
        """現在のタブを閉じる"""
        current = self.main_area.currentIndex()
        if current >= 0:
            self.close_tab(current)
    
    def refresh_current(self):
        """現在のタブを更新"""
        current_widget = self.main_area.currentWidget()
        if hasattr(current_widget, 'refresh'):
            current_widget.refresh()
    
    def update_stats(self):
        """統計情報を更新"""
        try:
            stats = db_manager.get_statistics()
            
            self.stats_labels["customers"].setText(f"取引先: {stats.get('customers_count', 0)}")
            self.stats_labels["products"].setText(f"商品: {stats.get('products_count', 0)}")
            self.stats_labels["active_loans"].setText(f"貸出中: {stats.get('active_loans_count', 0)}")
            self.stats_labels["pending_invoices"].setText(f"未入金: {stats.get('pending_invoices_count', 0)}")
            
            # ステータスバー更新
            self.status_db.setText("DB: 正常")
            
        except Exception as e:
            print(f"統計更新エラー: {e}")
            self.status_db.setText("DB: エラー")
    
    def update_theme(self):
        """テーマを更新"""
        self.load_theme()
    
    def on_data_changed(self, table_name: str, action: str):
        """データ変更時の処理"""
        self.status_message.setText(f"{table_name} {action}")
        
        # 統計更新
        QTimer.singleShot(1000, self.update_stats)
    
    def show_error(self, title: str, message: str = None):
        """エラーダイアログ表示"""
        if message is None:
            message = title
            title = "エラー"
        
        QMessageBox.critical(self, title, message)
    
    def show_success(self, message: str):
        """成功メッセージ表示"""
        self.status_message.setText(message)
        QTimer.singleShot(3000, lambda: self.status_message.setText("準備完了"))
    
    # メニューアクション実装
    def new_file(self):
        """新規作成"""
        print("新規作成")
    
    def import_data(self):
        """データインポート"""
        print("データインポート")
    
    def export_data(self):
        """データエクスポート"""
        print("データエクスポート")
    
    def print_document(self):
        """印刷"""
        print("印刷")
    
    def show_search(self):
        """検索画面表示"""
        self.open_module("search")
    
    def toggle_theme(self):
        """テーマ切り替え"""
        current_theme = config_manager.get("app.theme")
        new_theme = "dark" if current_theme == "light" else "light"
        config_manager.set_theme(new_theme)
        self.show_success(f"{new_theme}テーマに切り替えました")
    
    def create_backup(self):
        """バックアップ作成"""
        if db_manager.create_backup():
            self.show_success("バックアップを作成しました")
        else:
            self.show_error("バックアップ作成に失敗しました")
    
    def optimize_database(self):
        """データベース最適化"""
        if db_manager.optimize_database():
            self.show_success("データベースを最適化しました")
        else:
            self.show_error("最適化に失敗しました")
    
    def show_ai_settings(self):
        """AI設定ダイアログ表示"""
        try:
            dialog = AISettingsDialog(ai_assistant, self)
            dialog.exec()
        except Exception as e:
            print(f"AI設定ダイアログエラー: {e}")
            QMessageBox.critical(self, "エラー", f"AI設定の表示に失敗しました:\n{str(e)}")
    
    def show_accessibility_settings(self):
        """アクセシビリティ設定ダイアログ表示"""
        try:
            dialog = AccessibilityDialog(accessibility_manager, self)
            dialog.settings_changed.connect(self.on_accessibility_changed)
            dialog.exec()
        except Exception as e:
            print(f"アクセシビリティ設定ダイアログエラー: {e}")
            QMessageBox.critical(self, "エラー", f"アクセシビリティ設定の表示に失敗しました:\n{str(e)}")
    
    def on_accessibility_changed(self):
        """アクセシビリティ設定変更時"""
        # フォント・テーマ再適用
        accessibility_manager.apply_font_to_application()
        accessibility_manager.apply_high_contrast()
        
        # 全ウィジェットにスタイル再適用
        self.load_theme()
        
        accessibility_manager.speak("アクセシビリティ設定を適用しました")
    
    def show_help(self):
        """ヘルプ表示"""
        help_text = """
業務支援システム v3.0 ヘルプ

【ショートカットキー】
Ctrl+1-9: 各モジュールへ移動
Ctrl+D: ダッシュボード表示
Ctrl+T: テーマ切り替え
F5: 現在画面を更新
Esc: タブを閉じる

【基本操作】
- 左サイドバーから各機能にアクセス
- タブで複数画面を同時表示
- 右クリックメニューで詳細操作

【AI・音声機能】
- AI音声コマンドで自然言語操作
- アクセシビリティ設定で読み上げ機能
- 高齢者対応の大きな文字・ボタン
        """
        
        QMessageBox.information(self, "ヘルプ", help_text)
    
    def show_about(self):
        """アプリケーション情報表示"""
        from ..core.app import create_app
        app_info = create_app().get_app_info()
        
        about_text = f"""
{app_info['name']}
バージョン: {app_info['version']}

PyQt6 ベースのモダンな業務管理システム
AI統合・高齢者対応・音声コマンド機能搭載

Qt バージョン: {app_info['qt_version']}
Python バージョン: {app_info['python_version'].split()[0]}

© 2024 Business System Development Team
        """
        
        QMessageBox.about(self, "このアプリケーションについて", about_text)
    
    def closeEvent(self, event):
        """ウィンドウ閉じる時の処理"""
        # 確認ダイアログ
        reply = QMessageBox.question(
            self, "終了確認", 
            "アプリケーションを終了しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 設定保存
            from ..core.app import create_app
            app = create_app()
            app.shutdown()
            
            event.accept()
        else:
            event.ignore()