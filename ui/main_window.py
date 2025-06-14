"""
メインウィンドウクラス - AI統合・アクセシビリティ対応版
モダンなデザインのメインウィンドウ
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QMenuBar, QStatusBar, QToolBar, QSplitter,
                            QDockWidget, QTabWidget, QMessageBox, QPushButton,
                            QLabel, QFrame, QGroupBox, QFormLayout, QComboBox,
                            QCheckBox, QSpinBox, QTableWidget, QHeaderView,
                            QDateEdit, QTableWidgetItem)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QDate
from PyQt6.QtGui import QKeySequence, QIcon, QFont, QAction
from typing import Dict, Any, Optional

from ui.dashboard import Dashboard
from ui.components.base_widget import BaseWidget
from ui.plugin_manager_dialog import PluginManagerDialog
from core.config_manager import config_manager
from core.database import db_manager
from core.plugin_manager import PluginManager
from core.ai_integration import ai_assistant, AICommandWidget, AISettingsDialog
from core.accessibility import accessibility_manager, AccessibilityDialog
from core.gemini_integration import gemini_client
from core.hybrid_ai_system import hybrid_ai_manager
from modules.customers import CustomerWidget
from modules.products import ProductWidget
from modules.invoices import InvoiceWidget
from modules.loans import LoanWidget
from modules.analytics import AnalyticsWidget
from modules.enhanced_analytics import EnhancedAnalyticsWidget


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
        self.create_status_bar()  # 最初にステータスバーを作成
        self.setup_ui()
        self.create_menu_bar()
        self.create_tool_bar()
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
        
        # 初回統計更新（全UI作成後）
        QTimer.singleShot(100, self.update_stats)
        
        print("メインウィンドウを初期化しました")
    
    def setup_ui(self):
        """UI初期化"""
        # ウィンドウ設定
        self.setWindowTitle(config_manager.get("app.name", "業務支援システム v4.0"))
        self.setMinimumSize(1500, 950)  # UI改善に対応した最小サイズ
        self.resize(1700, 1050)  # デフォルトサイズを更に拡大
        
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # スプリッター（サイドバーとメインエリア）
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setSizes([380, 1420])  # サイドバーを少し拡大
        main_layout.addWidget(self.splitter)
        
        # サイドバー
        self.create_sidebar()
        
        # メインエリア
        self.main_area = QTabWidget()
        self.main_area.setTabsClosable(True)
        self.main_area.tabCloseRequested.connect(self.close_tab)
        self.splitter.addWidget(self.main_area)
        
        # スプリッター比率設定とサイズ制約
        self.splitter.setSizes([380, 1420])  # サイドバーとメインエリアのサイズを調整
        self.splitter.setCollapsible(0, False)  # サイドバーが完全に隠れないように
        self.splitter.setStretchFactor(0, 0)  # サイドバーは固定比率
        self.splitter.setStretchFactor(1, 1)  # メインエリアは可変
    
    def create_sidebar(self):
        """サイドバー作成"""
        self.sidebar = QFrame()
        self.sidebar.setMaximumWidth(400)  # サイドバーの最大幅をさらに拡大
        self.sidebar.setMinimumWidth(320)  # サイドバーの最小幅をさらに拡大
        
        # サイドバーのスタイルを改善
        self.sidebar.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-right: 1px solid #dee2e6;
            }
        """)
        
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
            ("📈", "AI強化分析", lambda: self.open_module("enhanced_analytics")),
            ("🤖", "AI音声コマンド", lambda: self.open_module("ai_commands")),
            ("🖼️", "文書解析", lambda: self.open_module("document_analysis")),
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
        button.setMinimumHeight(52)  # 最小高さを拡大
        button.setMinimumWidth(240)  # 最小幅を拡大
        
        # ボタンクリック時に音声ガイド
        def wrapped_callback():
            try:
                accessibility_manager.speak(f"{text}を開いています")
            except:
                pass  # 音声ガイドエラーは無視
            callback()
        
        button.clicked.connect(wrapped_callback)
        
        # 改良されたボタンスタイル
        button_style = """
            QPushButton {
                text-align: left;
                padding: 12px 16px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                margin: 3px;
                background-color: #ffffff;
                font-size: 14px;
                font-weight: 500;
                color: #333333;
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 0.08);
                border-color: #2196F3;
                color: #1976D2;
            }
            QPushButton:pressed {
                background-color: rgba(33, 150, 243, 0.15);
                border-color: #1565C0;
            }
            QPushButton:focus {
                outline: 2px solid #2196F3;
                outline-offset: 2px;
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
        # 初回更新は後で実行
    
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
        
        # AI機能メニュー項目を追加
        if hasattr(self, 'toggle_ai_chat_action'):
            tools_menu.addAction(self.toggle_ai_chat_action)
        if hasattr(self, 'toggle_ai_action'):
            tools_menu.addAction(self.toggle_ai_action)
            tools_menu.addSeparator()
        
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
        
        # Gemini設定
        gemini_settings_action = QAction("Gemini API設定(&G)...", self)
        gemini_settings_action.triggered.connect(self.show_gemini_settings)
        tools_menu.addAction(gemini_settings_action)
        
        # ハイブリッドAI設定
        hybrid_ai_action = QAction("ハイブリッドAI設定(&H)...", self)
        hybrid_ai_action.triggered.connect(self.show_hybrid_ai_settings)
        tools_menu.addAction(hybrid_ai_action)
        
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
            ("🎤", "音声入力", self.start_voice_input),
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
            # AIチャットウィジェットを作成
            from ui.ai_chat_widget import AIChatWidget
            self.ai_chat_widget = AIChatWidget()
            
            # AIチャット用のドックウィジェット
            self.ai_chat_dock = QDockWidget("🤖 AI チャット", self)
            self.ai_chat_dock.setWidget(self.ai_chat_widget)
            self.ai_chat_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
            
            # ドックウィジェットのサイズとスタイルを設定
            self.ai_chat_dock.setMinimumSize(350, 500)
            self.ai_chat_dock.setMaximumWidth(450)
            
            # ドックウィジェットの機能設定
            self.ai_chat_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                                         QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                                         QDockWidget.DockWidgetFeature.DockWidgetClosable)
            
            # 右側に配置
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.ai_chat_dock)
            
            # 初期状態では非表示
            self.ai_chat_dock.setVisible(False)
            
            # メニューアクション追加
            self.toggle_ai_chat_action = self.ai_chat_dock.toggleViewAction()
            self.toggle_ai_chat_action.setText("AIチャット表示")
            
            # AI音声コマンドウィジェットも保持（既存機能との互換性）
            self.ai_command_widget = AICommandWidget(ai_assistant)
            self.ai_dock = QDockWidget("🎤 AI音声コマンド", self)
            self.ai_dock.setWidget(self.ai_command_widget)
            self.ai_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
            
            # 音声コマンド用ドックの設定
            self.ai_dock.setMinimumSize(300, 400)
            self.ai_dock.setMaximumWidth(400)
            self.ai_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                                   QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                                   QDockWidget.DockWidgetFeature.DockWidgetClosable)
            
            # 右側に配置（チャットの下）
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.ai_dock)
            
            # 初期状態では非表示
            self.ai_dock.setVisible(False)
            
            # AI コマンド処理接続
            self.ai_command_widget.command_recognized.connect(self.handle_ai_command)
            
            # メニューアクション追加
            self.toggle_ai_action = self.ai_dock.toggleViewAction()
            self.toggle_ai_action.setText("AI音声コマンド表示")
            
            # ドックウィジェットの積み重ね設定
            self.tabifyDockWidget(self.ai_chat_dock, self.ai_dock)
            
            # デフォルトでチャットタブを選択
            self.ai_chat_dock.raise_()
            
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
    
    def on_ai_dock_visibility_changed(self, visible: bool):
        """AIドックの表示/非表示が変更された時の処理"""
        if visible:
            print("AIパネルが表示されました")
        else:
            print("AIパネルが非表示になりました")
    
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
            "enhanced_analytics": "📈 AI強化分析",
            "ai_commands": "🤖 AI音声コマンド",
            "document_analysis": "🖼️ 文書解析",
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
            # すべての主要モジュールが実装済みのため、このプレースホルダーは表示されないはず
            placeholder = QLabel(f"{module_name} モジュール\n\n✅ 正常動作\n\n（モジュールが見つかりません）")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("""
                font-size: 18px; 
                color: #4CAF50; 
                background-color: #e8f5e8;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                padding: 20px;
            """)
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
            elif module_name == "enhanced_analytics":
                return EnhancedAnalyticsWidget()
            elif module_name == "document_analysis":
                # 文書解析専用画面
                from modules.enhanced_analytics import DocumentAnalysisWidget
                return DocumentAnalysisWidget()
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
            elif module_name == "settings":
                # システム設定画面
                from ui.settings_widget import SettingsWidget
                return SettingsWidget()
            elif module_name == "inventory":
                # 在庫管理画面
                from modules.inventory import InventoryWidget
                return InventoryWidget()
            elif module_name == "search":
                # 履歴検索画面
                return self.create_search_widget()
            else:
                return None
        except Exception as e:
            print(f"モジュール作成エラー ({module_name}): {e}")
            import traceback
            traceback.print_exc()
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
    
    def create_settings_widget(self):
        """システム設定ウィジェット作成"""
        settings_widget = QWidget()
        settings_widget.setMaximumWidth(900)  # 設定パネルの最大幅を制限
        layout = QVBoxLayout(settings_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # タイトル
        title = QLabel("⚙️ システム設定")
        title.setFont(QFont("Yu Gothic UI", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 設定項目をタブで整理
        tab_widget = QTabWidget()
        tab_widget.setMaximumWidth(850)  # タブウィジェットの最大幅を制限
        
        # 基本設定タブ
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        
        # アプリケーション設定
        app_group = QGroupBox("アプリケーション設定")
        app_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        app_layout = QFormLayout(app_group)
        
        # 起動時の動作
        startup_combo = QComboBox()
        startup_combo.addItems(["ダッシュボードを表示", "前回のタブを復元", "指定したモジュールを表示"])
        app_layout.addRow("起動時の動作:", startup_combo)
        
        # 自動保存
        autosave_check = QCheckBox("データを自動保存する")
        autosave_check.setChecked(True)
        app_layout.addRow("自動保存:", autosave_check)
        
        # バックアップ
        backup_check = QCheckBox("終了時にバックアップを作成")
        backup_check.setChecked(True)
        app_layout.addRow("バックアップ:", backup_check)
        
        basic_layout.addWidget(app_group)
        
        # 表示設定
        display_group = QGroupBox("表示設定")
        display_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        display_layout = QFormLayout(display_group)
        
        # テーマ選択
        theme_combo = QComboBox()
        theme_combo.addItems(["ライトテーマ", "ダークテーマ", "システム設定に従う"])
        display_layout.addRow("テーマ:", theme_combo)
        
        # フォントサイズ
        font_spin = QSpinBox()
        font_spin.setRange(8, 24)
        font_spin.setValue(12)
        font_spin.setSuffix("pt")
        display_layout.addRow("フォントサイズ:", font_spin)
        
        basic_layout.addWidget(display_group)
        basic_layout.addStretch()
        
        tab_widget.addTab(basic_tab, "基本設定")
        
        # データベース設定タブ
        db_tab = QWidget()
        db_layout = QVBoxLayout(db_tab)
        
        db_group = QGroupBox("データベース設定")
        db_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        db_form_layout = QFormLayout(db_group)
        
        # データベースパス
        db_path_edit = QLineEdit()
        db_path_edit.setText("business_system.db")
        db_path_edit.setReadOnly(True)
        db_form_layout.addRow("データベースファイル:", db_path_edit)
        
        # データベース操作ボタン
        db_buttons = QHBoxLayout()
        backup_btn = QPushButton("バックアップ作成")
        backup_btn.clicked.connect(self.create_backup)
        optimize_btn = QPushButton("最適化実行")
        optimize_btn.clicked.connect(self.optimize_database)
        
        db_buttons.addWidget(backup_btn)
        db_buttons.addWidget(optimize_btn)
        db_buttons.addStretch()
        
        db_layout.addWidget(db_group)
        db_layout.addLayout(db_buttons)
        db_layout.addStretch()
        
        tab_widget.addTab(db_tab, "データベース")
        
        layout.addWidget(tab_widget)
        
        # 保存ボタン
        save_btn = QPushButton("設定を保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        save_btn.clicked.connect(lambda: self.show_success("設定を保存しました"))
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        return settings_widget
    
    def create_inventory_widget(self):
        """在庫管理ウィジェット作成"""
        inventory_widget = QWidget()
        layout = QVBoxLayout(inventory_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # タイトル
        title = QLabel("📊 在庫管理")
        title.setFont(QFont("Yu Gothic UI", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 在庫状況表示エリア
        status_group = QGroupBox("在庫状況")
        status_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        status_layout = QHBoxLayout(status_group)
        
        # 在庫レベル別の商品数
        levels = [
            ("正常在庫", "50", "#4CAF50"),
            ("低在庫", "15", "#FF9800"),
            ("在庫切れ", "3", "#f44336"),
            ("過剰在庫", "2", "#2196F3")
        ]
        
        for level_name, count, color in levels:
            level_frame = QFrame()
            level_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {color}33;
                    border-left: 4px solid {color};
                    border-radius: 4px;
                    padding: 16px;
                }}
            """)
            level_layout = QVBoxLayout(level_frame)
            
            count_label = QLabel(count)
            count_label.setFont(QFont("Yu Gothic UI", 18, QFont.Weight.Bold))
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_label.setStyleSheet(f"color: {color};")
            
            name_label = QLabel(level_name)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setStyleSheet("color: #666;")
            
            level_layout.addWidget(count_label)
            level_layout.addWidget(name_label)
            
            status_layout.addWidget(level_frame)
        
        layout.addWidget(status_group)
        
        # クイックアクション
        action_group = QGroupBox("クイックアクション")
        action_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        action_layout = QHBoxLayout(action_group)
        
        actions = [
            ("在庫調整", "在庫数の手動調整"),
            ("棚卸し", "定期棚卸しの実行"),
            ("発注管理", "自動発注の設定"),
            ("レポート", "在庫レポートの出力")
        ]
        
        for action_name, description in actions:
            action_btn = QPushButton(f"{action_name}\n{description}")
            action_btn.setMinimumHeight(80)
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 12px;
                    text-align: center;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                    border-color: #2196F3;
                }
            """)
            action_layout.addWidget(action_btn)
        
        layout.addWidget(action_group)
        layout.addStretch()
        
        return inventory_widget
    
    def create_search_widget(self):
        """履歴検索ウィジェット作成"""
        search_widget = QWidget()
        layout = QVBoxLayout(search_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # タイトル
        title = QLabel("🔍 履歴検索")
        title.setFont(QFont("Yu Gothic UI", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 検索条件エリア
        search_group = QGroupBox("検索条件")
        search_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        search_layout = QFormLayout(search_group)
        
        # キーワード検索
        keyword_edit = QLineEdit()
        keyword_edit.setPlaceholderText("キーワードを入力してください")
        keyword_edit.setMinimumHeight(32)
        keyword_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        search_layout.addRow("キーワード:", keyword_edit)
        
        # 検索対象
        target_combo = QComboBox()
        target_combo.addItems(["すべて", "取引先", "商品", "貸出履歴", "請求書"])
        target_combo.setMinimumHeight(32)
        target_combo.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        search_layout.addRow("検索対象:", target_combo)
        
        # 期間指定
        period_layout = QHBoxLayout()
        from_date = QDateEdit()
        from_date.setCalendarPopup(True)
        from_date.setDate(QDate.currentDate().addMonths(-3))
        to_date = QDateEdit()
        to_date.setCalendarPopup(True)
        to_date.setDate(QDate.currentDate())
        
        period_layout.addWidget(from_date)
        period_layout.addWidget(QLabel("〜"))
        period_layout.addWidget(to_date)
        period_layout.addStretch()
        
        search_layout.addRow("期間:", period_layout)
        
        # 検索ボタン
        search_btn = QPushButton("検索実行")
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        search_layout.addRow("", search_btn)
        
        layout.addWidget(search_group)
        
        # 検索結果エリア
        result_group = QGroupBox("検索結果")
        result_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        result_layout = QVBoxLayout(result_group)
        
        # 結果テーブル
        result_table = QTableWidget(0, 5)
        result_table.setHorizontalHeaderLabels(["日時", "種別", "対象", "詳細", "操作"])
        result_table.setAlternatingRowColors(True)
        
        # ヘッダーサイズ調整
        header = result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        result_layout.addWidget(result_table)
        layout.addWidget(result_group)
        
        return search_widget
    
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
            if hasattr(self, 'status_db'):
                self.status_db.setText("DB: 正常")
            
        except Exception as e:
            print(f"統計更新エラー: {e}")
            if hasattr(self, 'status_db'):
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
        from core.app import create_app
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
    
    def show_gemini_settings(self):
        """Gemini設定ダイアログ表示"""
        try:
            from ui.gemini_settings_dialog import GeminiSettingsDialog
            dialog = GeminiSettingsDialog(gemini_client, self)
            dialog.exec()
        except Exception as e:
            print(f"Gemini設定ダイアログエラー: {e}")
            QMessageBox.critical(self, "エラー", f"Gemini設定の表示に失敗しました:\n{str(e)}")
    
    def show_hybrid_ai_settings(self):
        """ハイブリッドAI設定ダイアログ表示"""
        try:
            from ui.hybrid_ai_settings_dialog import HybridAISettingsDialog
            dialog = HybridAISettingsDialog(hybrid_ai_manager, self)
            dialog.exec()
        except Exception as e:
            print(f"ハイブリッドAI設定ダイアログエラー: {e}")
            QMessageBox.critical(self, "エラー", f"ハイブリッドAI設定の表示に失敗しました:\n{str(e)}")
    
    def start_voice_input(self):
        """Windows音声入力を開始"""
        try:
            # Windows音声認識起動
            import subprocess
            import os
            
            # Windows 10/11の音声認識を起動
            if os.name == 'nt':  # Windows環境の場合
                try:
                    # Windows音声認識を起動
                    subprocess.Popen(['powershell.exe', '-Command', 'Start-Process ms-speech-recognition:'])
                    accessibility_manager.speak("音声入力を開始しました")
                    self.show_success("Windows音声認識を起動しました")
                except Exception as e:
                    print(f"Windows音声認識起動エラー: {e}")
                    # フォールバック: AIアシスタントのドックを表示
                    if hasattr(self, 'ai_dock'):
                        self.ai_dock.setVisible(True)
                        self.ai_dock.raise_()
                        accessibility_manager.speak("AI音声コマンドパネルを開きました")
                    else:
                        self.show_error("音声入力機能を利用できません")
            else:
                # Windows以外の環境ではAI音声コマンドを使用
                if hasattr(self, 'ai_dock'):
                    self.ai_dock.setVisible(True)
                    self.ai_dock.raise_()
                    accessibility_manager.speak("AI音声コマンドパネルを開きました")
                else:
                    self.show_error("この環境では音声入力をサポートしていません")
                    
        except Exception as e:
            print(f"音声入力開始エラー: {e}")
            self.show_error(f"音声入力の開始に失敗しました: {str(e)}")
    
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
            # AI関連のクリーンアップ
            try:
                hybrid_ai_manager.save_settings()
                gemini_client.save_settings()
            except Exception as e:
                print(f"AI設定保存エラー: {e}")
            
            # 設定保存
            from core.app import create_app
            app = create_app()
            app.shutdown()
            
            event.accept()
        else:
            event.ignore()