"""
ベースウィジェットクラス
すべてのカスタムウィジェットの基底クラス
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette
from typing import Optional, Dict, Any

from core.config_manager import config_manager


class BaseWidget(QWidget):
    """ベースウィジェットクラス"""
    
    # 共通シグナル
    data_changed = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._animations = {}
        self._theme_data = {}
        self._ui_initialized = False
        self._fade_animation = None
        self._slide_animation = None
        
        # 設定変更の監視
        config_manager.theme_changed.connect(self.update_theme)
    
    def setup_ui(self):
        """UI初期化（サブクラスでオーバーライド）"""
        if not self._ui_initialized:
            self._ui_initialized = True
            # 初期化時にテーマとアニメーション設定を実行
            self.load_theme()
            self.setup_animations()
    
    def load_theme(self):
        """テーマデータを読み込み"""
        self._theme_data = config_manager.get_theme()
        self.apply_theme()
    
    def apply_theme(self):
        """テーマを適用"""
        colors = self._theme_data.get("colors", {})
        fonts = self._theme_data.get("fonts", {})
        
        # 背景色設定
        bg_color = colors.get("surface", "#FFFFFF")
        self.setStyleSheet(f"""
            BaseWidget {{
                background-color: {bg_color};
                color: {colors.get("text_primary", "#212121")};
                font-family: "{fonts.get("family", "Yu Gothic UI")}";
                font-size: {fonts.get("size_medium", 12)}px;
            }}
        """)
    
    def update_theme(self):
        """テーマ更新"""
        self.load_theme()
    
    def setup_animations(self):
        """アニメーション設定"""
        try:
            if not config_manager.get("ui.animation_enabled", True):
                return
            
            # フェードイン アニメーション
            self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
            self._fade_animation.setDuration(config_manager.get("ui.animation_duration", 300))
            self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            # スライドアニメーション
            self._slide_animation = QPropertyAnimation(self, b"geometry")
            self._slide_animation.setDuration(config_manager.get("ui.animation_duration", 300))
            self._slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        except Exception as e:
            print(f"アニメーション設定エラー: {e}")
            self._fade_animation = None
            self._slide_animation = None
    
    def fade_in(self, duration: Optional[int] = None):
        """フェードインアニメーション"""
        try:
            if not config_manager.get("ui.animation_enabled", True):
                return
            
            # アニメーションが初期化されていない場合は初期化
            if not hasattr(self, '_fade_animation') or self._fade_animation is None:
                self.setup_animations()
                
            # まだ初期化されていない場合はアニメーションをスキップ
            if not hasattr(self, '_fade_animation') or self._fade_animation is None:
                return
            
            if duration:
                self._fade_animation.setDuration(duration)
            
            self._fade_animation.setStartValue(0.0)
            self._fade_animation.setEndValue(1.0)
            self._fade_animation.start()
        except Exception as e:
            print(f"フェードインアニメーションエラー: {e}")
            # エラーが発生した場合はアニメーションを無効化
            self._fade_animation = None
    
    def fade_out(self, duration: Optional[int] = None):
        """フェードアウトアニメーション"""
        try:
            if not config_manager.get("ui.animation_enabled", True):
                return
            
            # アニメーションが初期化されていない場合は初期化
            if not hasattr(self, '_fade_animation') or self._fade_animation is None:
                self.setup_animations()
                
            # まだ初期化されていない場合はアニメーションをスキップ
            if not hasattr(self, '_fade_animation') or self._fade_animation is None:
                return
            
            if duration:
                self._fade_animation.setDuration(duration)
            
            self._fade_animation.setStartValue(1.0)
            self._fade_animation.setEndValue(0.0)
            self._fade_animation.start()
        except Exception as e:
            print(f"フェードアウトアニメーションエラー: {e}")
            self._fade_animation = None
    
    def slide_in_from_left(self, duration: Optional[int] = None):
        """左からスライドイン"""
        try:
            if not config_manager.get("ui.animation_enabled", True):
                return
            
            # アニメーションが初期化されていない場合は初期化
            if not hasattr(self, '_slide_animation') or self._slide_animation is None:
                self.setup_animations()
                
            # まだ初期化されていない場合はアニメーションをスキップ
            if not hasattr(self, '_slide_animation') or self._slide_animation is None:
                return
            
            if duration:
                self._slide_animation.setDuration(duration)
            
            current_rect = self.geometry()
            start_rect = QRect(-current_rect.width(), current_rect.y(), 
                              current_rect.width(), current_rect.height())
            
            self._slide_animation.setStartValue(start_rect)
            self._slide_animation.setEndValue(current_rect)
            self._slide_animation.start()
        except Exception as e:
            print(f"スライドアニメーションエラー: {e}")
            self._slide_animation = None
    
    def show_loading(self, message: str = "読み込み中..."):
        """ローディング表示"""
        # 実装予定: スピナーやプログレスバー
        pass
    
    def hide_loading(self):
        """ローディング非表示"""
        # 実装予定
        pass
    
    def show_success_message(self, message: str, duration: int = 3000):
        """成功メッセージ表示"""
        self.show_temporary_message(message, "success", duration)
    
    def show_error_message(self, message: str, duration: int = 5000):
        """エラーメッセージ表示"""
        self.show_temporary_message(message, "error", duration)
        self.error_occurred.emit(message)
    
    def show_temporary_message(self, message: str, message_type: str = "info", duration: int = 3000):
        """一時的なメッセージ表示"""
        # メッセージラベルを作成
        msg_label = QLabel(message)
        msg_label.setParent(self)
        
        # スタイル適用
        colors = self._theme_data.get("colors", {})
        if message_type == "success":
            bg_color = colors.get("success", "#4CAF50")
        elif message_type == "error":
            bg_color = colors.get("error", "#F44336")
        else:
            bg_color = colors.get("primary", "#2196F3")
        
        msg_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
        """)
        
        # 位置設定
        msg_label.adjustSize()
        x = (self.width() - msg_label.width()) // 2
        y = 20
        msg_label.move(x, y)
        msg_label.show()
        
        # フェードイン
        fade_in = QPropertyAnimation(msg_label, b"windowOpacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.start()
        
        # 自動削除タイマー
        QTimer.singleShot(duration, lambda: self._remove_message(msg_label))
    
    def _remove_message(self, label: QLabel):
        """メッセージを削除"""
        if label and label.parent():
            # フェードアウト
            fade_out = QPropertyAnimation(label, b"windowOpacity")
            fade_out.setDuration(200)
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.finished.connect(label.deleteLater)
            fade_out.start()
    
    def get_theme_color(self, color_name: str, default: str = "#000000") -> str:
        """テーマカラーを取得"""
        colors = self._theme_data.get("colors", {})
        return colors.get(color_name, default)
    
    def get_theme_font(self, font_type: str = "medium") -> QFont:
        """テーマフォントを取得"""
        fonts = self._theme_data.get("fonts", {})
        family = fonts.get("family", "Yu Gothic UI")
        size = fonts.get(f"size_{font_type}", 12)
        
        font = QFont(family, size)
        return font
    
    def create_card_frame(self) -> QFrame:
        """カード風フレームを作成"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Box)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.get_theme_color("surface")};
                border: 1px solid {self.get_theme_color("border")};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        return frame
    
    def create_primary_button(self, text: str) -> QPushButton:
        """プライマリボタンを作成"""
        button = QPushButton(text)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.get_theme_color("primary")};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {self.get_theme_color("primary")};
                background-color: #1976D2;
            }}
            QPushButton:pressed {{
                background-color: {self.get_theme_color("primary")};
                background-color: #1976D2;
            }}
        """)
        return button
    
    def create_secondary_button(self, text: str) -> QPushButton:
        """セカンダリボタンを作成"""
        button = QPushButton(text)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.get_theme_color("secondary")};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {self.get_theme_color("secondary")};
                background-color: #1976D2;
            }}
        """)
        return button