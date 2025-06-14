"""
フォーム上部ボタン方式のヘッダーウィジェット
メインウィンドウのUI改善案として、各フォームの上部に機能ボタンを並べる方式
"""

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QLabel, QFrame, QToolButton, QButtonGroup,
                            QSizePolicy, QSpacerItem)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon


class FormHeaderWidget(QWidget):
    """フォーム上部のヘッダーウィジェット"""
    
    # シグナル定義
    action_triggered = pyqtSignal(str)  # アクション名
    voice_input_requested = pyqtSignal()  # 音声入力要求
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self.setup_ui()
    
    def setup_ui(self):
        """UI初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ヘッダーフレーム
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-bottom: 2px solid #e9ecef;
                padding: 8px;
            }
        """)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 8, 16, 8)
        
        # タイトルとボタンエリア
        top_layout = QHBoxLayout()
        
        # タイトル
        if self.title:
            title_label = QLabel(self.title)
            title_label.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
            title_label.setStyleSheet("color: #333333; padding: 4px 0;")
            top_layout.addWidget(title_label)
        
        # スペーサー
        top_layout.addStretch()
        
        # 音声入力ボタン
        voice_btn = QPushButton("🎤 音声入力")
        voice_btn.setStyleSheet(self.get_voice_button_style())
        voice_btn.clicked.connect(self.voice_input_requested.emit)
        voice_btn.setToolTip("Windows音声認識を起動します")
        top_layout.addWidget(voice_btn)
        
        header_layout.addLayout(top_layout)
        
        # 機能ボタンエリア
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(8)
        header_layout.addLayout(self.button_layout)
        
        layout.addWidget(header_frame)
        
        # コンテンツエリア（サブクラスで使用）
        self.content_area = QWidget()
        layout.addWidget(self.content_area, 1)
    
    def add_action_button(self, text: str, action_name: str, icon: str = "", 
                         primary: bool = False, tooltip: str = ""):
        """アクションボタンを追加"""
        button_text = f"{icon} {text}" if icon else text
        button = QPushButton(button_text)
        
        if primary:
            button.setStyleSheet(self.get_primary_button_style())
        else:
            button.setStyleSheet(self.get_secondary_button_style())
        
        if tooltip:
            button.setToolTip(tooltip)
        
        button.clicked.connect(lambda: self.action_triggered.emit(action_name))
        self.button_layout.addWidget(button)
        
        return button
    
    def add_button_group(self, buttons_config: list):
        """ボタングループを追加
        
        Args:
            buttons_config: [(text, action_name, icon, primary, tooltip), ...]
        """
        for config in buttons_config:
            text, action_name = config[:2]
            icon = config[2] if len(config) > 2 else ""
            primary = config[3] if len(config) > 3 else False
            tooltip = config[4] if len(config) > 4 else ""
            
            self.add_action_button(text, action_name, icon, primary, tooltip)
        
        # スペーサーを追加して右寄せを防ぐ
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, 
                           QSizePolicy.Policy.Minimum)
        self.button_layout.addItem(spacer)
    
    def get_primary_button_style(self):
        """プライマリボタンのスタイル"""
        return """
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:focus {
                outline: 2px solid #80bdff;
                outline-offset: 2px;
            }
        """
    
    def get_secondary_button_style(self):
        """セカンダリボタンのスタイル"""
        return """
            QPushButton {
                background-color: #f8f9fa;
                color: #495057;
                border: 1px solid #ced4da;
                padding: 10px 16px;
                border-radius: 6px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
                border-color: #6c757d;
            }
            QPushButton:focus {
                outline: 2px solid #80bdff;
                outline-offset: 2px;
            }
        """
    
    def get_voice_button_style(self):
        """音声入力ボタンのスタイル"""
        return """
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 13px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """


class DashboardHeaderWidget(FormHeaderWidget):
    """ダッシュボード用ヘッダーウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__("🏠 ダッシュボード", parent)
        self.setup_dashboard_buttons()
    
    def setup_dashboard_buttons(self):
        """ダッシュボード用ボタンを設定"""
        buttons = [
            ("新規登録", "new_record", "➕", True, "新しいレコードを作成"),
            ("データ更新", "refresh", "🔄", False, "最新データに更新"),
            ("レポート出力", "report", "📊", False, "各種レポートを出力"),
            ("設定", "settings", "⚙️", False, "システム設定を開く")
        ]
        self.add_button_group(buttons)


class InventoryHeaderWidget(FormHeaderWidget):
    """在庫管理用ヘッダーウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__("📊 在庫管理", parent)
        self.setup_inventory_buttons()
    
    def setup_inventory_buttons(self):
        """在庫管理用ボタンを設定"""
        buttons = [
            ("在庫調整", "adjust_stock", "📝", True, "在庫数を手動調整"),
            ("入庫処理", "receive_stock", "📥", False, "商品入庫を処理"),
            ("出庫処理", "ship_stock", "📤", False, "商品出庫を処理"),
            ("棚卸し", "stocktaking", "📋", False, "定期棚卸しを実行"),
            ("在庫アラート", "alerts", "🔔", False, "在庫アラートの設定"),
            ("レポート", "inventory_report", "📈", False, "在庫レポートを出力")
        ]
        self.add_button_group(buttons)


class CustomerHeaderWidget(FormHeaderWidget):
    """取引先管理用ヘッダーウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__("👥 取引先管理", parent)
        self.setup_customer_buttons()
    
    def setup_customer_buttons(self):
        """取引先管理用ボタンを設定"""
        buttons = [
            ("新規登録", "new_customer", "👤", True, "新しい取引先を登録"),
            ("一括インポート", "import", "📥", False, "CSVから一括インポート"),
            ("一括エクスポート", "export", "📤", False, "データを一括エクスポート"),
            ("住所確認", "verify_address", "🗺️", False, "住所の正確性を確認"),
            ("重複チェック", "check_duplicates", "🔍", False, "重複データをチェック")
        ]
        self.add_button_group(buttons)


class ProductHeaderWidget(FormHeaderWidget):
    """商品管理用ヘッダーウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__("📦 商品管理", parent)
        self.setup_product_buttons()
    
    def setup_product_buttons(self):
        """商品管理用ボタンを設定"""
        buttons = [
            ("新規商品", "new_product", "📦", True, "新しい商品を登録"),
            ("価格更新", "update_prices", "💰", False, "商品価格を一括更新"),
            ("カテゴリ管理", "manage_categories", "🏷️", False, "商品カテゴリを管理"),
            ("画像アップロード", "upload_images", "🖼️", False, "商品画像をアップロード"),
            ("バーコード印刷", "print_barcodes", "🏷️", False, "バーコードラベルを印刷")
        ]
        self.add_button_group(buttons)


# 使用例とテスト用のサンプルウィンドウ
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("フォームヘッダーウィジェット テスト")
            self.setGeometry(100, 100, 1000, 700)
            
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            layout = QVBoxLayout(central_widget)
            
            # 各種ヘッダーウィジェットをテスト
            widgets = [
                DashboardHeaderWidget(),
                InventoryHeaderWidget(),
                CustomerHeaderWidget(),
                ProductHeaderWidget()
            ]
            
            for widget in widgets:
                widget.action_triggered.connect(self.handle_action)
                widget.voice_input_requested.connect(self.handle_voice_input)
                layout.addWidget(widget)
            
            layout.addStretch()
        
        def handle_action(self, action_name):
            print(f"アクション実行: {action_name}")
        
        def handle_voice_input(self):
            print("音声入力要求")
    
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())