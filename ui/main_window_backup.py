"""
メインウィンドウクラス
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
from ..modules.customers import CustomerWidget
from ..modules.products import ProductWidget
from ..modules.invoices import InvoiceWidget


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
        
        # UI構築
        self.setup_ui()
        self.create_menu_bar()
        self.create_tool_bar()
        self.create_status_bar()
        self.setup_shortcuts()
        self.load_theme()
        
        # 初期表示
        self.show_dashboard()
        
        # シグナル接続
        self.setup_signals()
        
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
            ("📈", "売上集計", lambda: self.open_module("reports")),
            ("⚙️", "システム設定", lambda: self.open_module("settings"))
        ]\n        \n        for icon, text, callback in menu_items:\n            btn = self.create_nav_button(icon, text, callback)\n            nav_layout.addWidget(btn)\n        \n        layout.addWidget(nav_frame)\n    \n    def create_nav_button(self, icon: str, text: str, callback) -> QPushButton:\n        \"\"\"ナビゲーションボタン作成\"\"\"\n        button = QPushButton(f\"{icon} {text}\")\n        button.clicked.connect(callback)\n        button.setStyleSheet(\"\"\"\n            QPushButton {\n                text-align: left;\n                padding: 12px 16px;\n                border: none;\n                border-radius: 4px;\n                font-size: 14px;\n                margin: 2px;\n            }\n            QPushButton:hover {\n                background-color: rgba(33, 150, 243, 0.1);\n            }\n            QPushButton:pressed {\n                background-color: rgba(33, 150, 243, 0.2);\n            }\n        \"\"\")\n        return button\n    \n    def create_stats_area(self, layout):\n        \"\"\"統計情報エリア作成\"\"\"\n        stats_frame = QFrame()\n        stats_frame.setStyleSheet(\"\"\"\n            QFrame {\n                background-color: rgba(33, 150, 243, 0.05);\n                border-radius: 8px;\n                padding: 16px;\n                margin: 8px;\n            }\n        \"\"\")\n        \n        stats_layout = QVBoxLayout(stats_frame)\n        \n        # タイトル\n        title = QLabel(\"📊 システム状況\")\n        title.setFont(QFont(\"Yu Gothic UI\", 12, QFont.Weight.Bold))\n        stats_layout.addWidget(title)\n        \n        # 統計ラベル\n        self.stats_labels = {\n            \"customers\": QLabel(\"取引先: -\"),\n            \"products\": QLabel(\"商品: -\"),\n            \"active_loans\": QLabel(\"貸出中: -\"),\n            \"pending_invoices\": QLabel(\"未入金: -\")\n        }\n        \n        for label in self.stats_labels.values():\n            label.setStyleSheet(\"color: #555; font-size: 11px; margin: 2px;\")\n            stats_layout.addWidget(label)\n        \n        layout.addWidget(stats_frame)\n        \n        # 統計更新タイマー\n        self.stats_timer = QTimer()\n        self.stats_timer.timeout.connect(self.update_stats)\n        self.stats_timer.start(30000)  # 30秒間隔\n        self.update_stats()  # 初回更新\n    \n    def create_menu_bar(self):\n        \"\"\"メニューバー作成\"\"\"\n        menubar = self.menuBar()\n        \n        # ファイルメニュー\n        file_menu = menubar.addMenu(\"ファイル(&F)\")\n        \n        # 新規作成\n        new_action = QAction(\"新規作成(&N)\", self)\n        new_action.setShortcut(QKeySequence.StandardKey.New)\n        new_action.triggered.connect(self.new_file)\n        file_menu.addAction(new_action)\n        \n        file_menu.addSeparator()\n        \n        # インポート/エクスポート\n        import_action = QAction(\"インポート(&I)...\", self)\n        import_action.triggered.connect(self.import_data)\n        file_menu.addAction(import_action)\n        \n        export_action = QAction(\"エクスポート(&E)...\", self)\n        export_action.triggered.connect(self.export_data)\n        file_menu.addAction(export_action)\n        \n        file_menu.addSeparator()\n        \n        # 印刷\n        print_action = QAction(\"印刷(&P)\", self)\n        print_action.setShortcut(QKeySequence.StandardKey.Print)\n        print_action.triggered.connect(self.print_document)\n        file_menu.addAction(print_action)\n        \n        file_menu.addSeparator()\n        \n        # 終了\n        exit_action = QAction(\"終了(&X)\", self)\n        exit_action.setShortcut(QKeySequence.StandardKey.Quit)\n        exit_action.triggered.connect(self.close)\n        file_menu.addAction(exit_action)\n        \n        # 編集メニュー\n        edit_menu = menubar.addMenu(\"編集(&E)\")\n        \n        undo_action = QAction(\"元に戻す(&U)\", self)\n        undo_action.setShortcut(QKeySequence.StandardKey.Undo)\n        edit_menu.addAction(undo_action)\n        \n        redo_action = QAction(\"やり直し(&R)\", self)\n        redo_action.setShortcut(QKeySequence.StandardKey.Redo)\n        edit_menu.addAction(redo_action)\n        \n        edit_menu.addSeparator()\n        \n        find_action = QAction(\"検索(&F)...\", self)\n        find_action.setShortcut(QKeySequence.StandardKey.Find)\n        find_action.triggered.connect(self.show_search)\n        edit_menu.addAction(find_action)\n        \n        # 表示メニュー\n        view_menu = menubar.addMenu(\"表示(&V)\")\n        \n        dashboard_action = QAction(\"ダッシュボード(&D)\", self)\n        dashboard_action.setShortcut(QKeySequence(\"Ctrl+D\"))\n        dashboard_action.triggered.connect(self.show_dashboard)\n        view_menu.addAction(dashboard_action)\n        \n        view_menu.addSeparator()\n        \n        # テーマ切り替え\n        theme_action = QAction(\"ダークテーマ切り替え(&T)\", self)\n        theme_action.setShortcut(QKeySequence(\"Ctrl+T\"))\n        theme_action.triggered.connect(self.toggle_theme)\n        view_menu.addAction(theme_action)\n        \n        # ツールメニュー\n        tools_menu = menubar.addMenu(\"ツール(&T)\")\n        \n        backup_action = QAction(\"バックアップ作成(&B)\", self)\n        backup_action.triggered.connect(self.create_backup)\n        tools_menu.addAction(backup_action)\n        \n        optimize_action = QAction(\"データベース最適化(&O)\", self)\n        optimize_action.triggered.connect(self.optimize_database)\n        tools_menu.addAction(optimize_action)\n        \n        tools_menu.addSeparator()\n        \n        settings_action = QAction(\"設定(&S)...\", self)\n        settings_action.setShortcut(QKeySequence.StandardKey.Preferences)\n        settings_action.triggered.connect(lambda: self.open_module(\"settings\"))\n        tools_menu.addAction(settings_action)\n        \n        # ヘルプメニュー\n        help_menu = menubar.addMenu(\"ヘルプ(&H)\")\n        \n        manual_action = QAction(\"使い方(&U)\", self)\n        manual_action.setShortcut(QKeySequence.StandardKey.HelpContents)\n        manual_action.triggered.connect(self.show_help)\n        help_menu.addAction(manual_action)\n        \n        help_menu.addSeparator()\n        \n        about_action = QAction(\"このアプリケーションについて(&A)\", self)\n        about_action.triggered.connect(self.show_about)\n        help_menu.addAction(about_action)\n    \n    def create_tool_bar(self):\n        \"\"\"ツールバー作成\"\"\"\n        toolbar = QToolBar(\"メインツールバー\")\n        toolbar.setMovable(False)\n        \n        # よく使う機能のボタン\n        actions = [\n            (\"🏠\", \"ダッシュボード\", self.show_dashboard),\n            (\"➕\", \"新規作成\", self.new_file),\n            (\"🔍\", \"検索\", self.show_search),\n            (\"💾\", \"バックアップ\", self.create_backup),\n            (\"⚙️\", \"設定\", lambda: self.open_module(\"settings\"))\n        ]\n        \n        for icon, tooltip, callback in actions:\n            action = QAction(icon, self)\n            action.setToolTip(tooltip)\n            action.triggered.connect(callback)\n            toolbar.addAction(action)\n            \n            if tooltip == \"検索\":\n                toolbar.addSeparator()\n        \n        self.addToolBar(toolbar)\n    \n    def create_status_bar(self):\n        \"\"\"ステータスバー作成\"\"\"\n        status_bar = QStatusBar()\n        \n        # メッセージエリア\n        self.status_message = QLabel(\"準備完了\")\n        status_bar.addWidget(self.status_message)\n        \n        # 右側に統計情報\n        status_bar.addPermanentWidget(QLabel(\"|\"))\n        \n        self.status_db = QLabel(\"DB: 接続中\")\n        status_bar.addPermanentWidget(self.status_db)\n        \n        self.setStatusBar(status_bar)\n    \n    def setup_shortcuts(self):\n        \"\"\"ショートカットキー設定\"\"\"\n        # モジュール切り替えショートカット\n        shortcuts = {\n            \"Ctrl+1\": lambda: self.open_module(\"customers\"),\n            \"Ctrl+2\": lambda: self.open_module(\"products\"),\n            \"Ctrl+3\": lambda: self.open_module(\"inventory\"),\n            \"Ctrl+4\": lambda: self.open_module(\"loans\"),\n            \"Ctrl+5\": lambda: self.open_module(\"invoices\"),\n            \"Ctrl+6\": lambda: self.open_module(\"search\"),\n            \"Ctrl+7\": lambda: self.open_module(\"reports\"),\n            \"F5\": self.refresh_current,\n            \"Escape\": self.close_current_tab\n        }\n        \n        for key, callback in shortcuts.items():\n            action = QAction(self)\n            action.setShortcut(QKeySequence(key))\n            action.triggered.connect(callback)\n            self.addAction(action)\n    \n    def load_theme(self):\n        \"\"\"テーマを読み込み\"\"\"\n        stylesheet = config_manager.get_stylesheet()\n        self.setStyleSheet(stylesheet)\n    \n    def setup_signals(self):\n        \"\"\"シグナル接続\"\"\"\n        # 設定変更\n        config_manager.theme_changed.connect(self.update_theme)\n        \n        # データベースイベント\n        db_manager.data_changed.connect(self.on_data_changed)\n        db_manager.error_occurred.connect(self.show_error)\n    \n    def show_dashboard(self):\n        \"\"\"ダッシュボードを表示\"\"\"\n        # 既存のダッシュボードタブを探す\n        for i in range(self.main_area.count()):\n            if self.main_area.tabText(i) == \"ダッシュボード\":\n                self.main_area.setCurrentIndex(i)\n                return\n        \n        # 新しいダッシュボードタブを作成\n        dashboard = Dashboard()\n        index = self.main_area.addTab(dashboard, \"🏠 ダッシュボード\")\n        self.main_area.setCurrentIndex(index)\n        \n        # ダッシュボードタブは閉じられないようにする\n        tab_bar = self.main_area.tabBar()\n        tab_bar.setTabButton(index, tab_bar.ButtonPosition.RightSide, None)\n    \n    def open_module(self, module_name: str):\n        \"\"\"モジュールを開く\"\"\"\n        print(f\"モジュールを開きます: {module_name}\")\n        \n        # タブが既に開いているかチェック\n        for i in range(self.main_area.count()):\n            if self.main_area.tabText(i).endswith(module_name):\n                self.main_area.setCurrentIndex(i)\n                return\n        \n        # 新しいタブを作成（実装予定）\n        placeholder = QLabel(f\"{module_name} モジュール\\n\\n実装中...\")\n        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)\n        placeholder.setStyleSheet(\"font-size: 18px; color: #666;\")\n        \n        module_names = {\n            \"customers\": \"👥 取引先管理\",\n            \"products\": \"📦 商品管理\",\n            \"inventory\": \"📊 在庫管理\",\n            \"loans\": \"🛠 貸出処理\",\n            \"invoices\": \"📄 請求書作成\",\n            \"search\": \"🔍 履歴検索\",\n            \"reports\": \"📈 売上集計\",\n            \"settings\": \"⚙️ システム設定\"\n        }\n        \n        tab_name = module_names.get(module_name, module_name)\n        index = self.main_area.addTab(placeholder, tab_name)\n        self.main_area.setCurrentIndex(index)\n        \n        self.module_requested.emit(module_name)\n    \n    def close_tab(self, index: int):\n        \"\"\"タブを閉じる\"\"\"\n        if self.main_area.tabText(index) != \"🏠 ダッシュボード\":\n            self.main_area.removeTab(index)\n    \n    def close_current_tab(self):\n        \"\"\"現在のタブを閉じる\"\"\"\n        current = self.main_area.currentIndex()\n        if current >= 0:\n            self.close_tab(current)\n    \n    def refresh_current(self):\n        \"\"\"現在のタブを更新\"\"\"\n        current_widget = self.main_area.currentWidget()\n        if hasattr(current_widget, 'refresh'):\n            current_widget.refresh()\n    \n    def update_stats(self):\n        \"\"\"統計情報を更新\"\"\"\n        try:\n            stats = db_manager.get_statistics()\n            \n            self.stats_labels[\"customers\"].setText(f\"取引先: {stats.get('customers_count', 0)}\")\n            self.stats_labels[\"products\"].setText(f\"商品: {stats.get('products_count', 0)}\")\n            self.stats_labels[\"active_loans\"].setText(f\"貸出中: {stats.get('active_loans_count', 0)}\")\n            self.stats_labels[\"pending_invoices\"].setText(f\"未入金: {stats.get('pending_invoices_count', 0)}\")\n            \n            # ステータスバー更新\n            self.status_db.setText(\"DB: 正常\")\n            \n        except Exception as e:\n            print(f\"統計更新エラー: {e}\")\n            self.status_db.setText(\"DB: エラー\")\n    \n    def update_theme(self):\n        \"\"\"テーマを更新\"\"\"\n        self.load_theme()\n    \n    def on_data_changed(self, table_name: str, action: str):\n        \"\"\"データ変更時の処理\"\"\"\n        self.status_message.setText(f\"{table_name} {action}\")\n        \n        # 統計更新\n        QTimer.singleShot(1000, self.update_stats)\n    \n    def show_error(self, title: str, message: str = None):\n        \"\"\"エラーダイアログ表示\"\"\"\n        if message is None:\n            message = title\n            title = \"エラー\"\n        \n        QMessageBox.critical(self, title, message)\n    \n    def show_success(self, message: str):\n        \"\"\"成功メッセージ表示\"\"\"\n        self.status_message.setText(message)\n        QTimer.singleShot(3000, lambda: self.status_message.setText(\"準備完了\"))\n    \n    # メニューアクション実装\n    def new_file(self):\n        \"\"\"新規作成\"\"\"\n        print(\"新規作成\")\n    \n    def import_data(self):\n        \"\"\"データインポート\"\"\"\n        print(\"データインポート\")\n    \n    def export_data(self):\n        \"\"\"データエクスポート\"\"\"\n        print(\"データエクスポート\")\n    \n    def print_document(self):\n        \"\"\"印刷\"\"\"\n        print(\"印刷\")\n    \n    def show_search(self):\n        \"\"\"検索画面表示\"\"\"\n        self.open_module(\"search\")\n    \n    def toggle_theme(self):\n        \"\"\"テーマ切り替え\"\"\"\n        current_theme = config_manager.get(\"app.theme\")\n        new_theme = \"dark\" if current_theme == \"light\" else \"light\"\n        config_manager.set_theme(new_theme)\n        self.show_success(f\"{new_theme}テーマに切り替えました\")\n    \n    def create_backup(self):\n        \"\"\"バックアップ作成\"\"\"\n        if db_manager.create_backup():\n            self.show_success(\"バックアップを作成しました\")\n        else:\n            self.show_error(\"バックアップ作成に失敗しました\")\n    \n    def optimize_database(self):\n        \"\"\"データベース最適化\"\"\"\n        if db_manager.optimize_database():\n            self.show_success(\"データベースを最適化しました\")\n        else:\n            self.show_error(\"最適化に失敗しました\")\n    \n    def show_help(self):\n        \"\"\"ヘルプ表示\"\"\"\n        help_text = \"\"\"\n業務支援システム v3.0 ヘルプ\n\n【ショートカットキー】\nCtrl+1-7: 各モジュールへ移動\nCtrl+D: ダッシュボード表示\nCtrl+T: テーマ切り替え\nF5: 現在画面を更新\nEsc: タブを閉じる\n\n【基本操作】\n- 左サイドバーから各機能にアクセス\n- タブで複数画面を同時表示\n- 右クリックメニューで詳細操作\n        \"\"\"\n        \n        QMessageBox.information(self, \"ヘルプ\", help_text)\n    \n    def show_about(self):\n        \"\"\"アプリケーション情報表示\"\"\"\n        from ..core.app import create_app\n        app_info = create_app().get_app_info()\n        \n        about_text = f\"\"\"\n{app_info['name']}\nバージョン: {app_info['version']}\n\nPyQt6 ベースのモダンな業務管理システム\n\nQt バージョン: {app_info['qt_version']}\nPython バージョン: {app_info['python_version'].split()[0]}\n\n© 2024 Business System Development Team\n        \"\"\"\n        \n        QMessageBox.about(self, \"このアプリケーションについて\", about_text)\n    \n    def closeEvent(self, event):\n        \"\"\"ウィンドウ閉じる時の処理\"\"\"\n        # 確認ダイアログ\n        reply = QMessageBox.question(\n            self, \"終了確認\", \n            \"アプリケーションを終了しますか？\",\n            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,\n            QMessageBox.StandardButton.No\n        )\n        \n        if reply == QMessageBox.StandardButton.Yes:\n            # 設定保存\n            from ..core.app import create_app\n            app = create_app()\n            app.shutdown()\n            \n            event.accept()\n        else:\n            event.ignore()"