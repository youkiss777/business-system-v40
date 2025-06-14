#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v4.0 - Gemini API設定ダイアログ
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QLabel, QGroupBox,
    QMessageBox, QTextEdit, QCheckBox, QSpinBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GeminiTestThread(QThread):
    """Gemini接続テスト用スレッド"""
    
    test_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, gemini_client, test_prompt="こんにちは"):
        super().__init__()
        self.gemini_client = gemini_client
        self.test_prompt = test_prompt
    
    def run(self):
        try:
            result = self.gemini_client.generate_content(self.test_prompt)
            if "error" in result:
                self.test_completed.emit(False, result["error"])
            else:
                self.test_completed.emit(True, "接続テスト成功")
        except Exception as e:
            self.test_completed.emit(False, f"テストエラー: {str(e)}")


class GeminiSettingsDialog(QDialog):
    """Gemini API設定ダイアログ"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, gemini_client, parent=None):
        super().__init__(parent)
        self.gemini_client = gemini_client
        self.test_thread = None
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        """UI設定"""
        self.setWindowTitle("Gemini API設定")
        self.setModal(True)
        self.resize(500, 600)
        
        layout = QVBoxLayout(self)
        
        # タイトル
        title = QLabel("🤖 Google Gemini API設定")
        title.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2196F3; margin: 10px 0;")
        layout.addWidget(title)
        
        # 推奨モデル情報
        info_label = QLabel("✨ 推奨: Gemini 2.5 Pro系モデル（最新機能とパフォーマンス）")
        info_label.setStyleSheet("""
            background-color: #E8F5E8;
            color: #2E7D32;
            padding: 8px;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
            margin: 5px 0;
        """)
        layout.addWidget(info_label)
        
        # API設定グループ
        api_group = QGroupBox("API設定")
        api_layout = QFormLayout(api_group)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Google AI Studio で取得したAPIキーを入力")
        
        self.show_key_check = QCheckBox("APIキーを表示")
        self.show_key_check.toggled.connect(self.toggle_api_key_visibility)
        
        self.model_combo = QComboBox()
        # GeminiClientのget_available_models()から動的に取得
        available_models = [
            # === Gemini 2.5 (最新・推奨) ===
            "gemini-2.5-pro-exp-03-25",           # 最新実験版（推奨）
            "gemini-2.5-pro-preview-03-25",       # 最新プレビュー版
            "gemini-2.5-flash-preview-05-20",     # 高速版（改良版）
            "gemini-2.5-flash-preview-04-17",     # 高速版
            
            # === Gemini 2.0 ===
            "gemini-2.0-flash-exp",               # 実験版
            "gemini-2.0-flash",                   # 安定版
            "gemini-2.0-pro-exp",                 # Pro実験版
            "gemini-2.0-flash-thinking-exp",      # 思考型
            
            # === Gemini 1.5 (従来) ===
            "gemini-1.5-pro",                     # 高性能
            "gemini-1.5-flash",                   # 軽量
            "gemini-1.5-flash-8b",                # 超軽量版
            
            # === レガシー ===
            "gemini-1.0-pro"                      # 旧世代
        ]
        self.model_combo.addItems(available_models)
        
        api_layout.addRow("APIキー:", self.api_key_edit)
        api_layout.addRow("", self.show_key_check)
        api_layout.addRow("モデル:", self.model_combo)
        
        layout.addWidget(api_group)
        
        # 使用量設定グループ
        usage_group = QGroupBox("使用量設定")
        usage_layout = QFormLayout(usage_group)
        
        self.monthly_limit_spin = QSpinBox()
        self.monthly_limit_spin.setRange(1000, 10000000)
        self.monthly_limit_spin.setValue(1000000)
        self.monthly_limit_spin.setSuffix(" トークン")
        
        self.usage_warning_check = QCheckBox("使用量警告を有効")
        self.usage_warning_check.setChecked(True)
        
        usage_layout.addRow("月間制限:", self.monthly_limit_spin)
        usage_layout.addRow("", self.usage_warning_check)
        
        layout.addWidget(usage_group)
        
        # 現在の使用量表示
        status_group = QGroupBox("使用状況")
        status_layout = QVBoxLayout(status_group)
        
        self.usage_label = QLabel("月間使用量: -")
        self.remaining_label = QLabel("残り制限: -")
        self.status_label = QLabel("状態: 未設定")
        
        status_layout.addWidget(self.usage_label)
        status_layout.addWidget(self.remaining_label)
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(status_group)
        
        # テスト実行
        test_group = QGroupBox("接続テスト")
        test_layout = QVBoxLayout(test_group)
        
        self.test_btn = QPushButton("🔍 接続テスト実行")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        
        self.test_progress = QProgressBar()
        self.test_progress.setVisible(False)
        
        self.test_result = QTextEdit()
        self.test_result.setMaximumHeight(100)
        self.test_result.setPlaceholderText("テスト結果がここに表示されます...")
        
        test_layout.addWidget(self.test_btn)
        test_layout.addWidget(self.test_progress)
        test_layout.addWidget(self.test_result)
        
        layout.addWidget(test_group)
        
        # ボタン
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.cancel_btn = QPushButton("❌ キャンセル")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # シグナル接続
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)
        self.test_btn.clicked.connect(self.test_connection)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
    
    def toggle_api_key_visibility(self, checked):
        """APIキー表示切り替え"""
        if checked:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
    
    def load_current_settings(self):
        """現在の設定を読み込み"""
        try:
            self.api_key_edit.setText(self.gemini_client.api_key)
            
            # モデル選択
            model_index = self.model_combo.findText(self.gemini_client.model_name)
            if model_index >= 0:
                self.model_combo.setCurrentIndex(model_index)
            
            # 使用量設定
            self.monthly_limit_spin.setValue(self.gemini_client.monthly_limit)
            
            # 使用状況更新
            self.update_usage_display()
            
        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
    
    def update_usage_display(self):
        """使用量表示更新"""
        try:
            usage = self.gemini_client.monthly_token_usage
            limit = self.gemini_client.monthly_limit
            remaining = limit - usage
            
            self.usage_label.setText(f"月間使用量: {usage:,} トークン")
            self.remaining_label.setText(f"残り制限: {remaining:,} トークン")
            
            if self.gemini_client.is_enabled():
                self.status_label.setText("状態: ✅ 利用可能")
                self.status_label.setStyleSheet("color: #4CAF50;")
            else:
                self.status_label.setText("状態: ❌ 利用不可")
                self.status_label.setStyleSheet("color: #f44336;")
                
        except Exception as e:
            logger.error(f"使用量表示更新エラー: {e}")
    
    def test_connection(self):
        """接続テスト実行"""
        if not self.api_key_edit.text().strip():
            QMessageBox.warning(self, "警告", "APIキーを入力してください。")
            return
        
        # 一時的にAPIキーを設定
        original_key = self.gemini_client.api_key
        self.gemini_client.set_api_key(self.api_key_edit.text().strip())
        
        self.test_btn.setEnabled(False)
        self.test_progress.setVisible(True)
        self.test_progress.setRange(0, 0)
        self.test_result.setPlainText("接続テスト実行中...")
        
        # テスト実行
        self.test_thread = GeminiTestThread(self.gemini_client)
        self.test_thread.test_completed.connect(self.on_test_completed)
        self.test_thread.start()
    
    def on_test_completed(self, success: bool, message: str):
        """テスト完了時の処理"""
        self.test_progress.setVisible(False)
        self.test_btn.setEnabled(True)
        
        if success:
            self.test_result.setPlainText(f"✅ {message}")
            self.test_result.setStyleSheet("color: #4CAF50;")
        else:
            self.test_result.setPlainText(f"❌ {message}")
            self.test_result.setStyleSheet("color: #f44336;")
        
        # 使用量表示更新
        self.update_usage_display()
    
    def on_model_changed(self, model_name: str):
        """モデル変更時の処理"""
        try:
            # モデル別の説明を表示
            model_descriptions = {
                "gemini-2.5-pro-exp-03-25": "最新のGemini 2.5 Pro実験版 - 最高性能（推奨）",
                "gemini-2.5-pro-preview-03-25": "Gemini 2.5 Proプレビュー版 - 安定性重視",
                "gemini-2.5-flash-preview-05-20": "Gemini 2.5 Flash改良版 - 高速・軽量",
                "gemini-2.5-flash-preview-04-17": "Gemini 2.5 Flash版 - 高速処理",
                "gemini-2.0-flash-exp": "Gemini 2.0 Flash実験版 - バランス良好",
                "gemini-1.5-pro": "Gemini 1.5 Pro - 従来の高性能版",
                "gemini-1.5-flash": "Gemini 1.5 Flash - 軽量・高速",
            }
            
            description = model_descriptions.get(model_name, "選択されたモデル")
            
            # ステータスバーやツールチップで説明を表示
            self.model_combo.setToolTip(f"{model_name}\n{description}")
            
            logger.info(f"モデル選択変更: {model_name}")
            
        except Exception as e:
            logger.error(f"モデル変更処理エラー: {e}")
    
    def save_settings(self):
        """設定保存"""
        try:
            api_key = self.api_key_edit.text().strip()
            if not api_key:
                QMessageBox.warning(self, "警告", "APIキーを入力してください。")
                return
            
            # 設定適用
            self.gemini_client.set_api_key(api_key)
            self.gemini_client.model_name = self.model_combo.currentText()
            self.gemini_client.monthly_limit = self.monthly_limit_spin.value()
            
            # 設定保存（環境変数ファイルにも自動保存）
            self.gemini_client.save_settings()
            
            # 成功メッセージ
            selected_model = self.model_combo.currentText()
            message = f"Gemini API設定を保存しました。\n\n選択モデル: {selected_model}"
            if "2.5" in selected_model:
                message += "\n✨ 最新のGemini 2.5系モデルが設定されました！"
            
            QMessageBox.information(self, "設定保存完了", message)
            self.settings_changed.emit()
            self.accept()
            
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
            error_msg = f"設定保存に失敗しました:\n{str(e)}\n\n"
            error_msg += "確認項目:\n"
            error_msg += "- APIキーが正しく入力されているか\n"
            error_msg += "- インターネット接続が正常か\n"
            error_msg += "- 選択したモデルが利用可能か"
            QMessageBox.critical(self, "設定保存エラー", error_msg)