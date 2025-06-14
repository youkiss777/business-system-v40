"""
メインアプリケーションクラス
PyQt6 ベースのモダンな業務支援システム
"""

import sys
from PyQt6.QtWidgets import QApplication, QStyleFactory
from PyQt6.QtCore import QTimer, QTranslator, QLocale, QT_VERSION_STR
from PyQt6.QtGui import QIcon, QFont
from typing import Optional
import qdarkstyle

from .config_manager import config_manager
from .database import db_manager


class BusinessApp(QApplication):
    """メインアプリケーションクラス"""
    
    def __init__(self, argv):
        super().__init__(argv)
        
        # アプリケーション情報設定
        self.setApplicationName(config_manager.get("app.name", "業務支援システム v3.0"))
        self.setApplicationVersion(config_manager.get("app.version", "3.0.0"))
        self.setOrganizationName("Business System Corp")
        self.setOrganizationDomain("business-system.local")
        
        # 基本設定
        self._main_window = None
        self._translator = None
        self._auto_save_timer = None
        
        # 初期化
        self.initialize_app()
        self.setup_auto_save()
        self.setup_signals()
    
    def initialize_app(self):
        """アプリケーション初期化"""
        # フォント設定
        self.setup_fonts()
        
        # テーマ設定
        self.apply_theme()
        
        # 言語設定
        self.setup_language()
        
        # アイコン設定
        self.setup_icons()
        
        print("アプリケーションを初期化しました")
    
    def setup_fonts(self):
        """フォント設定"""
        theme = config_manager.get_theme()
        fonts = theme.get("fonts", {})
        
        font_family = fonts.get("family", "Yu Gothic UI")
        font_size = fonts.get("size_medium", 12)
        
        font = QFont(font_family, font_size)
        self.setFont(font)
        
        # 日本語フォントの優先設定
        font.setStyleHint(QFont.StyleHint.SansSerif)
        font.setWeight(QFont.Weight.Normal)
    
    def apply_theme(self):
        """テーマを適用"""
        current_theme = config_manager.get("app.theme", "light")
        
        if current_theme == "dark":
            # ダークテーマを適用
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())
        else:
            # ライトテーマ（カスタムスタイル）
            stylesheet = config_manager.get_stylesheet()
            self.setStyleSheet(stylesheet)
        
        # スタイル設定
        self.setStyle(QStyleFactory.create('Fusion'))
    
    def setup_language(self):
        """言語設定"""
        language = config_manager.get("app.language", "ja_JP")
        
        if language != "ja_JP":
            # 翻訳ファイルを読み込み（将来の多言語対応用）
            self._translator = QTranslator()
            if self._translator.load(f"resources/translations/{language}.qm"):
                self.installTranslator(self._translator)
    
    def setup_icons(self):
        """アイコン設定"""
        # アプリケーションアイコン
        icon_path = "resources/icons/app_icon.png"
        try:
            self.setWindowIcon(QIcon(icon_path))
        except:
            # デフォルトアイコン使用
            pass
    
    def setup_auto_save(self):
        """自動保存設定"""
        if config_manager.get("ui.auto_save", True):
            interval = config_manager.get("ui.auto_save_interval", 5) * 60 * 1000  # 分をミリ秒に変換
            
            self._auto_save_timer = QTimer()
            self._auto_save_timer.timeout.connect(self.auto_save)
            self._auto_save_timer.start(interval)
    
    def setup_signals(self):
        """シグナル接続設定"""
        # 設定変更時の処理
        config_manager.setting_changed.connect(self.on_setting_changed)
        config_manager.theme_changed.connect(self.on_theme_changed)
        
        # データベースイベント
        db_manager.error_occurred.connect(self.on_database_error)
    
    def set_main_window(self, window):
        """メインウィンドウを設定"""
        self._main_window = window
        
        # ウィンドウ設定を復元
        self.restore_window_settings()
    
    def restore_window_settings(self):
        """ウィンドウ設定を復元"""
        if not self._main_window:
            return
        
        # サイズ復元
        if config_manager.get("window.remember_size", True):
            width = config_manager.get("window.width", 1400)
            height = config_manager.get("window.height", 900)
            self._main_window.resize(width, height)
        
        # 最大化状態復元
        if config_manager.get("window.maximized", False):
            self._main_window.showMaximized()
    
    def save_window_settings(self):
        """ウィンドウ設定を保存"""
        if not self._main_window:
            return
        
        if config_manager.get("window.remember_size", True):
            size = self._main_window.size()
            config_manager.set("window.width", size.width())
            config_manager.set("window.height", size.height())
            config_manager.set("window.maximized", self._main_window.isMaximized())
    
    def auto_save(self):
        """自動保存実行"""
        try:
            # 設定保存
            config_manager.save_settings()
            
            # ウィンドウ設定保存
            self.save_window_settings()
            
            # データベース最適化（必要に応じて）
            if config_manager.get("database.auto_optimize", True):
                db_manager.optimize_database()
            
            print("自動保存を実行しました")
            
        except Exception as e:
            print(f"自動保存エラー: {e}")
    
    def on_setting_changed(self, key: str, value):
        """設定変更時の処理"""
        if key.startswith("ui.auto_save"):
            # 自動保存設定が変更された場合
            if self._auto_save_timer:
                self._auto_save_timer.stop()
            self.setup_auto_save()
        
        elif key.startswith("ui.animation"):
            # アニメーション設定が変更された場合
            self.update_animations()
    
    def on_theme_changed(self, theme_name: str):
        """テーマ変更時の処理"""
        self.apply_theme()
        
        # メインウィンドウに変更を通知
        if self._main_window and hasattr(self._main_window, 'update_theme'):
            self._main_window.update_theme()
    
    def on_database_error(self, error_message: str):
        """データベースエラー時の処理"""
        print(f"データベースエラー: {error_message}")
        
        # エラー通知（メインウィンドウがあれば）
        if self._main_window and hasattr(self._main_window, 'show_error'):
            self._main_window.show_error("データベースエラー", error_message)
    
    def update_animations(self):
        """アニメーション設定更新"""
        # アニメーション関連の更新処理
        # 実装は各UIコンポーネントで行う
        pass
    
    def shutdown(self):
        """アプリケーション終了処理"""
        try:
            # 自動保存タイマー停止
            if self._auto_save_timer:
                self._auto_save_timer.stop()
            
            # 最終保存
            self.save_window_settings()
            config_manager.save_settings()
            
            # データベース接続終了
            db_manager.close_session()
            
            # ログ記録
            db_manager.log_action("SHUTDOWN", "アプリケーション終了")
            
            print("アプリケーションを正常に終了しました")
            
        except Exception as e:
            print(f"終了処理エラー: {e}")
    
    def get_main_window(self):
        """メインウィンドウを取得"""
        return self._main_window
    
    def restart(self):
        """アプリケーション再起動"""
        try:
            # 現在の設定を保存
            self.shutdown()
            
            # 新しいプロセスを開始
            import os
            import subprocess
            
            python_path = sys.executable
            script_path = sys.argv[0]
            
            subprocess.Popen([python_path, script_path])
            
            # 現在のプロセスを終了
            self.quit()
            
        except Exception as e:
            print(f"再起動エラー: {e}")
    
    def create_backup(self):
        """バックアップ作成"""
        return db_manager.create_backup()
    
    def get_app_info(self) -> dict:
        """アプリケーション情報を取得"""
        return {
            "name": self.applicationName(),
            "version": self.applicationVersion(),
            "qt_version": QT_VERSION_STR,
            "python_version": sys.version,
            "database_path": db_manager.db_path,
            "config_dir": str(config_manager.config_dir),
            "theme": config_manager.get("app.theme"),
            "language": config_manager.get("app.language")
        }


def create_app(argv=None) -> BusinessApp:
    """アプリケーションインスタンスを作成"""
    if argv is None:
        argv = sys.argv
    
    app = BusinessApp(argv)
    return app