#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v3.0 - アクセシビリティ・高齢者対応機能
視認性向上、操作簡素化、音声ガイド等の機能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QComboBox, QCheckBox, QMessageBox, QHeaderView,
    QSplitter, QGroupBox, QLabel, QDateEdit, QSpinBox,
    QDoubleSpinBox, QFrame, QScrollArea, QSlider, QDialog,
    QApplication, QFontDialog, QColorDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings, QThread
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor
from typing import Optional, List, Dict, Any, Tuple
import logging
from pathlib import Path
import json

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class VoiceAssistant(QThread):
    """音声アシスタント（TTS）"""
    
    def __init__(self):
        super().__init__()
        self.tts_engine = None
        self.message_queue = []
        self.enabled = False
        
        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                # 音声設定
                voices = self.tts_engine.getProperty('voices')
                if voices:
                    # 日本語音声を探す
                    for voice in voices:
                        if 'japanese' in voice.name.lower() or 'ja' in voice.id.lower():
                            self.tts_engine.setProperty('voice', voice.id)
                            break
                
                # 速度・音量設定
                self.tts_engine.setProperty('rate', 150)  # 少し遅め
                self.tts_engine.setProperty('volume', 0.8)
                
                self.enabled = True
                logger.info("音声アシスタント初期化完了")
                
            except Exception as e:
                logger.error(f"音声エンジン初期化エラー: {e}")
                self.enabled = False
        else:
            logger.warning("pyttsx3が利用できません。音声機能は無効です。")
    
    def speak(self, text: str):
        """テキスト読み上げ"""
        try:
            if self.enabled and text:
                self.message_queue.append(text)
                if not self.isRunning():
                    self.start()
        except Exception as e:
            logger.error(f"音声読み上げ開始エラー: {e}")
            self.enabled = False
    
    def run(self):
        """音声読み上げスレッド実行"""
        while self.message_queue and self.enabled:
            try:
                message = self.message_queue.pop(0)
                if self.tts_engine:
                    self.tts_engine.say(message)
                    self.tts_engine.runAndWait()
            except Exception as e:
                logger.error(f"音声読み上げエラー: {e}")
    
    def set_enabled(self, enabled: bool):
        """音声機能有効/無効切り替え"""
        self.enabled = enabled and TTS_AVAILABLE
    
    def clear_queue(self):
        """音声キュークリア"""
        self.message_queue.clear()


class AccessibilityManager:
    """アクセシビリティ管理クラス"""
    
    def __init__(self):
        self.settings = QSettings("BusinessSystem", "Accessibility")
        self.voice_assistant = VoiceAssistant()
        self.current_font_size = 12
        self.current_theme = "light"
        self.high_contrast = False
        self.voice_enabled = False
        
        # 設定読み込み
        self.load_settings()
    
    def load_settings(self):
        """アクセシビリティ設定読み込み"""
        try:
            self.current_font_size = self.settings.value("font_size", 12, int)
            self.current_theme = self.settings.value("theme", "light", str)
            self.high_contrast = self.settings.value("high_contrast", False, bool)
            self.voice_enabled = self.settings.value("voice_enabled", False, bool)
            
            self.voice_assistant.set_enabled(self.voice_enabled)
            
        except Exception as e:
            logger.error(f"アクセシビリティ設定読み込みエラー: {e}")
    
    def save_settings(self):
        """アクセシビリティ設定保存"""
        try:
            self.settings.setValue("font_size", self.current_font_size)
            self.settings.setValue("theme", self.current_theme)
            self.settings.setValue("high_contrast", self.high_contrast)
            self.settings.setValue("voice_enabled", self.voice_enabled)
            
        except Exception as e:
            logger.error(f"アクセシビリティ設定保存エラー: {e}")
    
    def set_font_size(self, size: int):
        """フォントサイズ設定"""
        self.current_font_size = size
        self.apply_font_to_application()
        self.save_settings()
    
    def set_theme(self, theme: str):
        """テーマ設定"""
        self.current_theme = theme
        self.save_settings()
    
    def set_high_contrast(self, enabled: bool):
        """ハイコントラスト設定"""
        self.high_contrast = enabled
        self.apply_high_contrast()
        self.save_settings()
    
    def set_voice_enabled(self, enabled: bool):
        """音声機能設定"""
        self.voice_enabled = enabled
        self.voice_assistant.set_enabled(enabled)
        self.save_settings()
        
        if enabled:
            self.speak("音声ガイドを有効にしました")
        else:
            self.voice_assistant.clear_queue()
    
    def apply_font_to_application(self):
        """アプリケーション全体にフォント適用"""
        try:
            app = QApplication.instance()
            if app:
                font = QFont("Yu Gothic UI", self.current_font_size)
                app.setFont(font)
                
        except Exception as e:
            logger.error(f"フォント適用エラー: {e}")
    
    def apply_high_contrast(self):
        """ハイコントラスト適用"""
        try:
            app = QApplication.instance()
            if app and self.high_contrast:
                # ハイコントラストパレット
                palette = QPalette()
                palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
                palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42))
                palette.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66))
                palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(0, 0, 0))
                palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
                palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
                palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
                palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
                palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
                
                app.setPalette(palette)
                
        except Exception as e:
            logger.error(f"ハイコントラスト適用エラー: {e}")
    
    def speak(self, text: str):
        """音声読み上げ"""
        try:
            if self.voice_enabled and hasattr(self, 'voice_assistant') and self.voice_assistant:
                self.voice_assistant.speak(text)
        except Exception as e:
            logger.error(f"音声読み上げエラー: {e}")
            # 音声機能を無効化
            self.voice_enabled = False
    
    def get_large_button_style(self) -> str:
        """大きなボタン用スタイル"""
        return f"""
            QPushButton {{
                font-size: {self.current_font_size + 4}px;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
                min-height: 50px;
            }}
            QPushButton:hover {{
                background-color: #1976D2;
            }}
        """
    
    def get_accessible_table_style(self) -> str:
        """アクセシブルテーブル用スタイル"""
        return f"""
            QTableWidget {{
                font-size: {self.current_font_size + 2}px;
                gridline-color: #666;
                selection-background-color: #4CAF50;
                selection-color: white;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid #ddd;
            }}
            QHeaderView::section {{
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 10px;
                border: none;
            }}
        """


class AccessibilityDialog(QDialog):
    """アクセシビリティ設定ダイアログ"""
    
    # シグナル
    settings_changed = pyqtSignal()
    
    def __init__(self, accessibility_manager: AccessibilityManager, parent=None):
        super().__init__(parent)
        self.accessibility_manager = accessibility_manager
        self.setWindowTitle("アクセシビリティ設定")
        self.setModal(True)
        self.resize(500, 600)
        self.setup_ui()
        self.setup_connections()
        self.load_current_settings()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # フォント設定グループ
        font_group = QGroupBox("フォント・表示設定")
        font_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        font_layout = QFormLayout(font_group)
        
        # フォントサイズ
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setRange(10, 24)
        self.font_size_slider.setValue(12)
        self.font_size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.font_size_slider.setTickInterval(2)
        
        self.font_size_label = QLabel("12px")
        self.font_size_label.setStyleSheet("font-weight: bold; min-width: 50px;")
        
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(self.font_size_slider)
        font_size_layout.addWidget(self.font_size_label)
        
        font_layout.addRow("フォントサイズ:", font_size_layout)
        
        # フォント選択ボタン
        self.font_button = QPushButton("フォントを選択...")
        self.font_button.setStyleSheet("padding: 8px;")
        font_layout.addRow("フォント:", self.font_button)
        
        # ハイコントラスト
        self.high_contrast_check = QCheckBox("ハイコントラストモード")
        self.high_contrast_check.setStyleSheet("font-size: 14px;")
        font_layout.addRow("表示:", self.high_contrast_check)
        
        layout.addWidget(font_group)
        
        # 音声設定グループ
        voice_group = QGroupBox("音声・読み上げ設定")
        voice_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        voice_layout = QFormLayout(voice_group)
        
        # 音声ガイド有効/無効
        self.voice_enabled_check = QCheckBox("音声ガイドを有効にする")
        self.voice_enabled_check.setStyleSheet("font-size: 14px;")
        voice_layout.addRow("音声ガイド:", self.voice_enabled_check)
        
        # テスト読み上げボタン
        self.test_voice_btn = QPushButton("音声テスト")
        self.test_voice_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        voice_layout.addRow("テスト:", self.test_voice_btn)
        
        layout.addWidget(voice_group)
        
        # 操作支援グループ
        operation_group = QGroupBox("操作支援設定")
        operation_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        operation_layout = QFormLayout(operation_group)
        
        # 大きなボタン
        self.large_buttons_check = QCheckBox("大きなボタンを使用")
        self.large_buttons_check.setStyleSheet("font-size: 14px;")
        operation_layout.addRow("ボタン:", self.large_buttons_check)
        
        # 操作確認
        self.confirm_actions_check = QCheckBox("重要な操作で確認ダイアログを表示")
        self.confirm_actions_check.setStyleSheet("font-size: 14px;")
        operation_layout.addRow("確認:", self.confirm_actions_check)
        
        # 自動音声ガイド
        self.auto_guide_check = QCheckBox("画面切り替え時に音声ガイド")
        self.auto_guide_check.setStyleSheet("font-size: 14px;")
        operation_layout.addRow("ガイド:", self.auto_guide_check)
        
        layout.addWidget(operation_group)
        
        # プレビューエリア
        preview_group = QGroupBox("プレビュー")
        preview_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("これはプレビューテキストです。\nフォントサイズや表示設定の確認ができます。")
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 15px;
                font-size: 14px;
            }
        """)
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(preview_group)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.reset_btn = QPushButton("リセット")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        
        self.apply_btn = QPushButton("適用")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
    
    def setup_connections(self):
        """シグナル接続"""
        self.font_size_slider.valueChanged.connect(self.update_font_size_label)
        self.font_size_slider.valueChanged.connect(self.update_preview)
        self.font_button.clicked.connect(self.select_font)
        self.high_contrast_check.toggled.connect(self.update_preview)
        self.voice_enabled_check.toggled.connect(self.on_voice_enabled_changed)
        self.test_voice_btn.clicked.connect(self.test_voice)
        
        self.reset_btn.clicked.connect(self.reset_settings)
        self.apply_btn.clicked.connect(self.apply_settings)
        self.ok_btn.clicked.connect(self.accept_settings)
    
    def load_current_settings(self):
        """現在の設定を読み込み"""
        self.font_size_slider.setValue(self.accessibility_manager.current_font_size)
        self.high_contrast_check.setChecked(self.accessibility_manager.high_contrast)
        self.voice_enabled_check.setChecked(self.accessibility_manager.voice_enabled)
        
        self.update_font_size_label()
        self.update_preview()
    
    def update_font_size_label(self):
        """フォントサイズラベル更新"""
        size = self.font_size_slider.value()
        self.font_size_label.setText(f"{size}px")
    
    def update_preview(self):
        """プレビュー更新"""
        font_size = self.font_size_slider.value()
        high_contrast = self.high_contrast_check.isChecked()
        
        style = f"""
            QLabel {{
                font-size: {font_size}px;
                padding: 15px;
                border-radius: 4px;
                border: 1px solid #dee2e6;
        """
        
        if high_contrast:
            style += """
                background-color: #000;
                color: #fff;
                border-color: #fff;
            """
        else:
            style += """
                background-color: #f8f9fa;
                color: #000;
            """
        
        style += "}"
        self.preview_label.setStyleSheet(style)
    
    def select_font(self):
        """フォント選択"""
        current_font = QApplication.instance().font()
        font, ok = QFontDialog.getFont(current_font, self)
        
        if ok:
            self.selected_font = font
            self.font_button.setText(f"{font.family()} {font.pointSize()}pt")
    
    def on_voice_enabled_changed(self, enabled: bool):
        """音声有効/無効変更時"""
        self.test_voice_btn.setEnabled(enabled)
        if enabled:
            self.accessibility_manager.speak("音声ガイドが有効になりました")
    
    def test_voice(self):
        """音声テスト"""
        self.accessibility_manager.speak("これは音声テストです。音声ガイドが正常に動作しています。")
    
    def reset_settings(self):
        """設定リセット"""
        self.font_size_slider.setValue(12)
        self.high_contrast_check.setChecked(False)
        self.voice_enabled_check.setChecked(False)
        self.large_buttons_check.setChecked(False)
        self.confirm_actions_check.setChecked(True)
        self.auto_guide_check.setChecked(False)
        
        self.update_preview()
    
    def apply_settings(self):
        """設定適用"""
        # フォントサイズ
        self.accessibility_manager.set_font_size(self.font_size_slider.value())
        
        # ハイコントラスト
        self.accessibility_manager.set_high_contrast(self.high_contrast_check.isChecked())
        
        # 音声設定
        self.accessibility_manager.set_voice_enabled(self.voice_enabled_check.isChecked())
        
        # 設定変更シグナル発行
        self.settings_changed.emit()
        
        QMessageBox.information(self, "設定適用", "アクセシビリティ設定を適用しました。")
    
    def accept_settings(self):
        """設定確定"""
        self.apply_settings()
        self.accept()


# グローバルアクセシビリティマネージャー
accessibility_manager = AccessibilityManager()