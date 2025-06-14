#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v4.0 - AI チャットウィジェット
Gemini API統合によるAIテキスト入力・応答機能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QComboBox, QCheckBox, QMessageBox, QHeaderView,
    QSplitter, QGroupBox, QLabel, QDateEdit, QSpinBox,
    QDoubleSpinBox, QFrame, QScrollArea, QProgressBar, QDialog,
    QListWidget, QListWidgetItem, QPlainTextEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QDateTime, QSettings
from PyQt6.QtGui import QFont, QPixmap, QIcon, QColor, QTextCursor, QTextCharFormat
from typing import Optional, List, Dict, Any, Tuple
import logging
import json
from datetime import datetime, timedelta
import re

from ui.components.base_widget import BaseWidget
from core.database import db_manager
from core.config_manager import config_manager
from core.ai_integration import ai_assistant

logger = logging.getLogger(__name__)


class ChatMessage:
    """チャットメッセージクラス"""
    
    def __init__(self, content: str, is_user: bool, timestamp: datetime = None):
        self.content = content
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now()
        self.message_id = f"{self.timestamp.isoformat()}_{hash(content)}"


class ChatHistoryManager:
    """チャット履歴管理クラス"""
    
    def __init__(self):
        self.settings = QSettings("BusinessSystem", "AIChat")
        self.messages: List[ChatMessage] = []
        self.max_history = 100  # 最大履歴数
        self.load_history()
    
    def add_message(self, content: str, is_user: bool):
        """メッセージを追加"""
        message = ChatMessage(content, is_user)
        self.messages.append(message)
        
        # 履歴上限チェック
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
        
        self.save_history()
        return message
    
    def get_recent_messages(self, count: int = 10) -> List[ChatMessage]:
        """最近のメッセージを取得"""
        return self.messages[-count:] if count > 0 else self.messages
    
    def clear_history(self):
        """履歴をクリア"""
        self.messages.clear()
        self.save_history()
    
    def save_history(self):
        """履歴を保存"""
        try:
            history_data = []
            for msg in self.messages:
                history_data.append({
                    "content": msg.content,
                    "is_user": msg.is_user,
                    "timestamp": msg.timestamp.isoformat()
                })
            
            self.settings.setValue("chat_history", json.dumps(history_data))
        except Exception as e:
            logger.error(f"チャット履歴保存エラー: {e}")
    
    def load_history(self):
        """履歴を読み込み"""
        try:
            history_json = self.settings.value("chat_history", "[]")
            history_data = json.loads(history_json)
            
            self.messages = []
            for item in history_data:
                timestamp = datetime.fromisoformat(item["timestamp"])
                message = ChatMessage(item["content"], item["is_user"], timestamp)
                self.messages.append(message)
                
        except Exception as e:
            logger.error(f"チャット履歴読み込みエラー: {e}")
            self.messages = []


class AIResponseThread(QThread):
    """AI応答生成スレッド"""
    
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, prompt: str, conversation_history: List[ChatMessage] = None):
        super().__init__()
        self.prompt = prompt
        self.conversation_history = conversation_history or []
    
    def run(self):
        """AI応答生成実行"""
        try:
            # 会話履歴を含めたプロンプト作成
            full_prompt = self.build_conversation_prompt()
            
            # AI応答生成
            result = ai_assistant.process_natural_language_query(full_prompt)
            
            if "error" in result:
                self.error_occurred.emit(result["error"])
            else:
                # 応答テキストを抽出
                response_text = ""
                if "text" in result:
                    response_text = result["text"]
                elif "parameters" in result and "text" in result["parameters"]:
                    response_text = result["parameters"]["text"]
                elif "explanation" in result:
                    response_text = result["explanation"]
                else:
                    response_text = f"操作: {result.get('action', '不明')}\n説明: {result.get('explanation', '')}"
                
                self.response_ready.emit(response_text)
                
        except Exception as e:
            logger.error(f"AI応答生成エラー: {e}")
            self.error_occurred.emit(f"AI応答生成中にエラーが発生しました: {str(e)}")
    
    def build_conversation_prompt(self) -> str:
        """会話履歴を含むプロンプト作成"""
        # システムプロンプト
        system_prompt = """
あなたは業務支援システムのAIアシスタントです。
ユーザーの質問や要求に対して、親切で分かりやすい回答を提供してください。

対応可能な業務:
- 取引先管理（検索、登録、更新）
- 商品管理（在庫確認、価格照会）
- 貸出処理（新規貸出、返却処理）
- 請求書作成（月次請求、個別請求）
- 売上分析（レポート生成、トレンド分析）
- 在庫管理（在庫調整、低在庫アラート）

回答は以下の原則に従ってください:
1. 丁寧で分かりやすい日本語で回答
2. 具体的な操作手順を含める
3. 関連する機能やオプションも紹介
4. エラーや問題が発生した場合は代替案を提示
"""
        
        # 会話履歴を追加
        conversation = [system_prompt]
        
        # 最近の会話履歴（最大5件）
        recent_messages = self.conversation_history[-10:]
        for msg in recent_messages:
            role = "ユーザー" if msg.is_user else "AI"
            conversation.append(f"{role}: {msg.content}")
        
        # 現在の質問
        conversation.append(f"ユーザー: {self.prompt}")
        conversation.append("AI:")
        
        return "\n\n".join(conversation)


class AIChatWidget(BaseWidget):
    """AIチャットウィジェット"""
    
    # シグナル
    command_recognized = pyqtSignal(str, dict)  # コマンド名, パラメータ
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history_manager = ChatHistoryManager()
        self.ai_thread = None
        self.setup_ui()
        self.load_chat_history()
        
        # 自動保存タイマー
        self.save_timer = QTimer()
        self.save_timer.timeout.connect(self.history_manager.save_history)
        self.save_timer.start(60000)  # 1分ごと
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ヘッダー
        self.create_header(layout)
        
        # チャット表示エリア
        self.create_chat_area(layout)
        
        # 入力エリア
        self.create_input_area(layout)
        
        # ステータス表示
        self.create_status_area(layout)
    
    def create_header(self, layout):
        """ヘッダー作成"""
        header_layout = QHBoxLayout()
        
        # タイトル
        title = QLabel("🤖 AI チャット")
        title.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2196F3; margin: 5px 0;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # コントロールボタン
        self.clear_btn = QPushButton("🗑")
        self.clear_btn.setToolTip("チャット履歴をクリア")
        self.clear_btn.setFixedSize(30, 30)
        self.clear_btn.clicked.connect(self.clear_chat)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5722;
                color: white;
                border: none;
                border-radius: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        header_layout.addWidget(self.clear_btn)
        
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setToolTip("AI設定")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.clicked.connect(self.show_ai_settings)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #9c27b0;
                color: white;
                border: none;
                border-radius: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7b1fa2;
            }
        """)
        header_layout.addWidget(self.settings_btn)
        
        layout.addLayout(header_layout)
    
    def create_chat_area(self, layout):
        """チャット表示エリア作成"""
        # チャット履歴表示
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMaximumHeight(400)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(self.chat_display)
    
    def create_input_area(self, layout):
        """入力エリア作成"""
        input_group = QGroupBox("メッセージ入力")
        input_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        input_layout = QVBoxLayout(input_group)
        
        # テキスト入力エリア
        text_layout = QHBoxLayout()
        
        self.input_edit = QPlainTextEdit()
        self.input_edit.setMaximumHeight(80)
        self.input_edit.setPlaceholderText("質問や要求を入力してください...\n例: 田中商事の今月分の請求書を作成して")
        self.input_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QPlainTextEdit:focus {
                border-color: #2196F3;
            }
        """)
        
        # Enterキーでの送信を有効化
        self.input_edit.installEventFilter(self)
        
        text_layout.addWidget(self.input_edit)
        
        # 送信ボタン
        self.send_btn = QPushButton("送信")
        self.send_btn.setFixedSize(80, 80)
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        text_layout.addWidget(self.send_btn)
        
        input_layout.addLayout(text_layout)
        
        # クイックアクション
        quick_layout = QHBoxLayout()
        
        quick_actions = [
            ("在庫確認", "現在の在庫状況を教えて"),
            ("売上分析", "今月の売上分析をお願いします"),
            ("顧客検索", "顧客情報を検索したい"),
            ("請求書", "請求書を作成したい")
        ]
        
        for label, prompt in quick_actions:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #e3f2fd;
                    color: #1976d2;
                    border: 1px solid #2196f3;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #2196f3;
                    color: white;
                }
            """)
            btn.clicked.connect(lambda checked, p=prompt: self.set_quick_message(p))
            quick_layout.addWidget(btn)
        
        input_layout.addLayout(quick_layout)
        layout.addWidget(input_group)
    
    def create_status_area(self, layout):
        """ステータスエリア作成"""
        self.status_label = QLabel("準備完了")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e8f5e8;
                border: 1px solid #4caf50;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                color: #2e7d32;
            }
        """)
        
        # AI機能の状態確認
        if not ai_assistant.is_enabled():
            self.status_label.setText("AI機能が無効です（設定→AI機能で有効化してください）")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                    padding: 6px;
                    font-size: 12px;
                    color: #856404;
                }
            """)
            self.send_btn.setEnabled(False)
        
        layout.addWidget(self.status_label)
    
    def eventFilter(self, obj, event):
        """イベントフィルター（Enterキー処理）"""
        if obj == self.input_edit and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)
    
    def set_quick_message(self, message: str):
        """クイックメッセージ設定"""
        self.input_edit.setPlainText(message)
        self.input_edit.setFocus()
    
    def send_message(self):
        """メッセージ送信"""
        message_text = self.input_edit.toPlainText().strip()
        if not message_text:
            return
        
        if not ai_assistant.is_enabled():
            QMessageBox.warning(self, "AI機能無効", "AI機能が無効です。設定でAPIキーを設定してください。")
            return
        
        # ユーザーメッセージを履歴に追加
        user_message = self.history_manager.add_message(message_text, True)
        self.display_message(user_message)
        
        # 入力フィールドをクリア
        self.input_edit.clear()
        
        # AI応答を生成
        self.generate_ai_response(message_text)
    
    def generate_ai_response(self, user_message: str):
        """AI応答生成"""
        self.send_btn.setEnabled(False)
        self.status_label.setText("AI応答生成中...")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #fff3e0;
                border: 1px solid #ff9800;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                color: #f57c00;
            }
        """)
        
        # AI応答スレッド開始
        conversation_history = self.history_manager.get_recent_messages(10)
        self.ai_thread = AIResponseThread(user_message, conversation_history[:-1])  # 最後のメッセージ（今送ったもの）は除く
        self.ai_thread.response_ready.connect(self.on_ai_response)
        self.ai_thread.error_occurred.connect(self.on_ai_error)
        self.ai_thread.start()
    
    def on_ai_response(self, response_text: str):
        """AI応答受信"""
        # AI応答を履歴に追加
        ai_message = self.history_manager.add_message(response_text, False)
        self.display_message(ai_message)
        
        # UI状態をリセット
        self.send_btn.setEnabled(True)
        self.status_label.setText("準備完了")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e8f5e8;
                border: 1px solid #4caf50;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                color: #2e7d32;
            }
        """)
        
        # 入力フィールドにフォーカス
        self.input_edit.setFocus()
    
    def on_ai_error(self, error_message: str):
        """AI応答エラー"""
        # エラーメッセージを表示
        error_text = f"申し訳ございません。エラーが発生しました：\n{error_message}"
        ai_message = self.history_manager.add_message(error_text, False)
        self.display_message(ai_message)
        
        # UI状態をリセット
        self.send_btn.setEnabled(True)
        self.status_label.setText("エラーが発生しました")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #ffebee;
                border: 1px solid #f44336;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                color: #c62828;
            }
        """)
        
        self.input_edit.setFocus()
    
    def display_message(self, message: ChatMessage):
        """メッセージ表示"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # タイムスタンプ
        timestamp = message.timestamp.strftime("%H:%M")
        
        # メッセージスタイル設定
        if message.is_user:
            # ユーザーメッセージ
            user_format = QTextCharFormat()
            user_format.setForeground(QColor("#1976d2"))
            user_format.setFontWeight(QFont.Weight.Bold)
            
            cursor.setCharFormat(user_format)
            cursor.insertText(f"\n👤 あなた ({timestamp})\n")
            
            # メッセージ本文
            msg_format = QTextCharFormat()
            msg_format.setForeground(QColor("#333333"))
            cursor.setCharFormat(msg_format)
            cursor.insertText(f"{message.content}\n")
        else:
            # AI応答
            ai_format = QTextCharFormat()
            ai_format.setForeground(QColor("#4caf50"))
            ai_format.setFontWeight(QFont.Weight.Bold)
            
            cursor.setCharFormat(ai_format)
            cursor.insertText(f"\n🤖 AI アシスタント ({timestamp})\n")
            
            # メッセージ本文
            msg_format = QTextCharFormat()
            msg_format.setForeground(QColor("#333333"))
            cursor.setCharFormat(msg_format)
            cursor.insertText(f"{message.content}\n")
        
        # 自動スクロール
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()
    
    def load_chat_history(self):
        """チャット履歴読み込み"""
        self.chat_display.clear()
        
        # 履歴がある場合は表示
        messages = self.history_manager.get_recent_messages(20)
        if messages:
            for message in messages:
                self.display_message(message)
        else:
            # 初回メッセージ
            welcome_message = ChatMessage(
                "こんにちは！業務支援システムのAIアシスタントです。\n"
                "何かお手伝いできることがありましたら、お気軽にお声かけください。\n\n"
                "例：\n"
                "• 在庫状況を教えて\n"
                "• 今月の売上分析をお願いします\n"
                "• 田中商事の情報を検索して\n"
                "• 請求書を作成したい",
                False
            )
            self.display_message(welcome_message)
    
    def clear_chat(self):
        """チャットクリア"""
        reply = QMessageBox.question(
            self, "確認", 
            "チャット履歴をクリアしますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.clear_history()
            self.load_chat_history()
    
    def show_ai_settings(self):
        """AI設定表示"""
        try:
            from core.ai_integration import AISettingsDialog
            dialog = AISettingsDialog(ai_assistant, self)
            dialog.exec()
            
            # 設定変更後のステータス更新
            if ai_assistant.is_enabled():
                self.send_btn.setEnabled(True)
                self.status_label.setText("準備完了")
                self.status_label.setStyleSheet("""
                    QLabel {
                        background-color: #e8f5e8;
                        border: 1px solid #4caf50;
                        border-radius: 4px;
                        padding: 6px;
                        font-size: 12px;
                        color: #2e7d32;
                    }
                """)
            else:
                self.send_btn.setEnabled(False)
                self.status_label.setText("AI機能が無効です")
                self.status_label.setStyleSheet("""
                    QLabel {
                        background-color: #fff3cd;
                        border: 1px solid #ffeaa7;
                        border-radius: 4px;
                        padding: 6px;
                        font-size: 12px;
                        color: #856404;
                    }
                """)
        except Exception as e:
            logger.error(f"AI設定表示エラー: {e}")
            QMessageBox.critical(self, "エラー", f"AI設定の表示に失敗しました：{e}")
    
    def showEvent(self, event):
        """表示時の処理"""
        super().showEvent(event)
        self.input_edit.setFocus()