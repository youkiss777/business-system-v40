#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v3.0 - AI連携機能
OpenAI API、音声認識、自然言語処理による業務支援
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QComboBox, QCheckBox, QMessageBox, QHeaderView,
    QSplitter, QGroupBox, QLabel, QDateEdit, QSpinBox,
    QDoubleSpinBox, QFrame, QScrollArea, QProgressBar, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QSettings
from PyQt6.QtGui import QFont, QPixmap, QIcon
from typing import Optional, List, Dict, Any, Tuple, Callable
import logging
import json
import os
from datetime import datetime, date
import re

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import speech_recognition as sr
    import pyaudio
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

from core.database import Customer, Product, Loan, Invoice, db_manager
from core.config_manager import config_manager

logger = logging.getLogger(__name__)


class AIAssistant:
    """AI助手クラス"""
    
    def __init__(self):
        self.settings = QSettings("BusinessSystem", "AI")
        self.openai_api_key = ""
        self.gemini_api_key = ""
        self.openai_model = "gpt-3.5-turbo"
        self.enabled = False
        
        # 設定読み込み
        self.load_settings()
        
        # 設定管理システムからAI有効フラグを確認
        if not config_manager.is_ai_enabled():
            self.enabled = False
            logger.info("AI機能は設定により無効化されています")
            return
        
        # Geminiクライアントをインポートして使用
        try:
            from core.gemini_integration import gemini_client
            self.gemini_client = gemini_client
            if self.gemini_client.is_enabled():
                self.enabled = True
                logger.info("Gemini API初期化完了")
            else:
                logger.info("Gemini APIが利用できません。OpenAIにフォールバック")
        except Exception as e:
            logger.error(f"Gemini統合エラー: {e}")
        
        # OpenAI初期化（フォールバック）
        if OPENAI_AVAILABLE and self.openai_api_key and not self.enabled:
            try:
                openai.api_key = self.openai_api_key
                self.enabled = True
                logger.info("OpenAI API初期化完了")
            except Exception as e:
                logger.error(f"OpenAI API初期化エラー: {e}")
                self.enabled = False
        
        # 最終的に有効化されなかった場合の処理
        if not self.enabled:
            if not OPENAI_AVAILABLE:
                logger.warning("OpenAIライブラリが利用できません")
            if not self.openai_api_key and not self.gemini_api_key:
                logger.warning("AI APIキーが設定されていません")
            logger.info("AI機能を手動で有効化してください（設定→AI機能）")
    
    def load_settings(self):
        """AI設定読み込み"""
        try:
            # 環境設定ファイルから優先的に読み込み
            self.openai_api_key = config_manager.get_ai_setting("OPENAI_API_KEY", "")
            self.gemini_api_key = config_manager.get_ai_setting("GEMINI_API_KEY", "")
            
            if not self.openai_api_key:
                # フォールバックとしてQSettingsから読み込み
                self.openai_api_key = self.settings.value("openai_api_key", "", str)
            
            if not self.gemini_api_key:
                # フォールバックとしてQSettingsから読み込み
                self.gemini_api_key = self.settings.value("gemini_api_key", "", str)
                
            self.openai_model = self.settings.value("openai_model", "gpt-3.5-turbo", str)
            
            logger.info(f"AI設定読み込み: OpenAI={'設定済み' if self.openai_api_key else '未設定'}, Gemini={'設定済み' if self.gemini_api_key else '未設定'}")
            
        except Exception as e:
            logger.error(f"AI設定読み込みエラー: {e}")
    
    def save_settings(self):
        """AI設定保存"""
        try:
            # 環境設定ファイルにも保存
            config_manager.set_ai_setting("OPENAI_API_KEY", self.openai_api_key)
            # QSettingsにも保存（互換性のため）
            self.settings.setValue("openai_api_key", self.openai_api_key)
            self.settings.setValue("openai_model", self.openai_model)
        except Exception as e:
            logger.error(f"AI設定保存エラー: {e}")
    
    def set_api_key(self, api_key: str):
        """APIキー設定"""
        self.openai_api_key = api_key
        self.save_settings()
        
        if OPENAI_AVAILABLE and api_key:
            try:
                openai.api_key = api_key
                self.enabled = True
                logger.info("OpenAI APIキー設定完了")
            except Exception as e:
                logger.error(f"OpenAI APIキー設定エラー: {e}")
                self.enabled = False
    
    def is_enabled(self) -> bool:
        """AI機能有効状態"""
        # Geminiまたは OpenAI のどちらかが利用可能であれば有効
        gemini_available = hasattr(self, 'gemini_client') and self.gemini_client.is_enabled()
        openai_available = self.enabled and OPENAI_AVAILABLE and self.openai_api_key
        
        return config_manager.is_ai_enabled() and (gemini_available or openai_available)
    
    def process_natural_language_query(self, query: str) -> Dict[str, Any]:
        """自然言語クエリ処理"""
        if not self.is_enabled():
            return {"error": "AI機能が無効です"}
        
        try:
            # システムプロンプト
            system_prompt = """
あなたは業務支援システムのAIアシスタントです。
ユーザーの自然言語による指示を解析し、適切な業務操作を特定してください。

可能な操作:
1. 取引先検索 (search_customer)
2. 商品検索 (search_product)
3. 貸出登録 (create_loan)
4. 請求書作成 (create_invoice)
5. 売上分析 (analyze_sales)
6. 在庫確認 (check_inventory)

回答は以下のJSON形式で返してください:
{
    "action": "操作名",
    "parameters": {"パラメータ名": "値"},
    "confidence": 0.0-1.0,
    "explanation": "操作の説明"
}
"""
            
            full_prompt = f"{system_prompt}\n\nユーザーの質問: {query}"
            
            # Gemini APIを優先的に使用
            if hasattr(self, 'gemini_client') and self.gemini_client.is_enabled():
                response = self.gemini_client.generate_content(full_prompt)
                if "error" not in response:
                    content = response.get("text", "")
                else:
                    # Geminiでエラーが発生した場合はOpenAIにフォールバック
                    return self._fallback_to_openai_query(query, system_prompt)
            else:
                # OpenAI API呼び出し
                return self._fallback_to_openai_query(query, system_prompt)
            
            # JSON解析
            try:
                # JSONブロックを抽出
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                elif "{" in content and "}" in content:
                    # JSON部分を抽出
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1
                    content = content[json_start:json_end]
                
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # JSON形式でない場合はテキスト応答として処理
                return {
                    "action": "text_response",
                    "parameters": {"text": content},
                    "confidence": 0.8,
                    "explanation": "自然言語での回答"
                }
                
        except Exception as e:
            logger.error(f"自然言語クエリ処理エラー: {e}")
            return {"error": f"AI処理エラー: {str(e)}"}
    
    def _fallback_to_openai_query(self, query: str, system_prompt: str) -> Dict[str, Any]:
        """OpenAIにフォールバック"""
        try:
            if not OPENAI_AVAILABLE or not self.openai_api_key:
                return {"error": "OpenAI APIが利用できません"}
                
            response = openai.ChatCompletion.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                return {
                    "action": "text_response",
                    "parameters": {"text": content},
                    "confidence": 0.8,
                    "explanation": "自然言語での回答"
                }
        except Exception as e:
            logger.error(f"OpenAI フォールバックエラー: {e}")
            return {"error": f"OpenAI処理エラー: {str(e)}"}
    
    def generate_invoice_description(self, loan_data: List[Dict]) -> str:
        """請求書説明文生成"""
        if not self.is_enabled():
            return "請求書の詳細"
        
        try:
            # 貸出データを要約
            summary = []
            for loan in loan_data:
                summary.append(f"- {loan.get('product_name', '商品')}: {loan.get('quantity', 0)}点")
            
            summary_text = "\n".join(summary[:5])  # 最大5件
            
            prompt = f"""
以下の貸出データに基づいて、請求書に記載する丁寧で分かりやすい説明文を生成してください。

貸出内容:
{summary_text}

要件:
- 敬語を使用
- 簡潔で分かりやすく
- 100文字以内
- 請求書に適した文体
"""
            
            response = openai.ChatCompletion.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"請求書説明文生成エラー: {e}")
            return "請求書の詳細"
    
    def suggest_product_recommendations(self, customer_history: List[Dict]) -> List[str]:
        """商品推奨生成"""
        if not self.is_enabled():
            return []
        
        try:
            # 履歴データを要約
            history_text = []
            for item in customer_history[:10]:  # 最新10件
                history_text.append(f"- {item.get('product_name', '商品')}")
            
            history_summary = "\n".join(history_text)
            
            prompt = f"""
以下の顧客の貸出履歴に基づいて、おすすめの商品を3つ提案してください。

過去の利用履歴:
{history_summary}

条件:
- 履歴に基づいた適切な推奨
- 商品名のみをリストで回答
- 3つまで
"""
            
            response = openai.ChatCompletion.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            
            # 推奨商品を抽出
            recommendations = []
            for line in content.split('\n'):
                if line.strip() and not line.startswith('#'):
                    # リスト記号を除去
                    clean_line = re.sub(r'^[-•*]\s*', '', line.strip())
                    if clean_line:
                        recommendations.append(clean_line)
            
            return recommendations[:3]
            
        except Exception as e:
            logger.error(f"商品推奨生成エラー: {e}")
            return []


class VoiceRecognitionThread(QThread):
    """音声認識スレッド"""
    
    # シグナル
    speech_recognized = pyqtSignal(str)  # 認識されたテキスト
    recognition_started = pyqtSignal()
    recognition_stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.recognizer = None
        self.microphone = None
        self.is_listening = False
        
        if SPEECH_RECOGNITION_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()
                
                # マイク調整
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source)
                
                logger.info("音声認識初期化完了")
                
            except Exception as e:
                logger.error(f"音声認識初期化エラー: {e}")
                self.recognizer = None
    
    def start_listening(self):
        """音声認識開始"""
        if self.recognizer and not self.is_listening:
            self.is_listening = True
            self.start()
    
    def stop_listening(self):
        """音声認識停止"""
        self.is_listening = False
    
    def run(self):
        """音声認識スレッド実行"""
        if not self.recognizer:
            self.error_occurred.emit("音声認識が利用できません")
            return
        
        self.recognition_started.emit()
        
        try:
            while self.is_listening:
                with self.microphone as source:
                    # 音声取得
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                try:
                    # Google音声認識（日本語）
                    text = self.recognizer.recognize_google(audio, language='ja-JP')
                    if text:
                        self.speech_recognized.emit(text)
                        
                except sr.UnknownValueError:
                    # 音声が認識できない場合は継続
                    continue
                except sr.RequestError as e:
                    self.error_occurred.emit(f"音声認識サービスエラー: {e}")
                    break
                    
        except Exception as e:
            self.error_occurred.emit(f"音声認識エラー: {e}")
        
        finally:
            self.is_listening = False
            self.recognition_stopped.emit()


class AICommandWidget(QWidget):
    """AI音声コマンドウィジェット"""
    
    # シグナル
    command_recognized = pyqtSignal(str, dict)  # コマンド名, パラメータ
    
    def __init__(self, ai_assistant: AIAssistant, parent=None):
        super().__init__(parent)
        self.ai_assistant = ai_assistant
        self.voice_recognition = VoiceRecognitionThread()
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # タイトル
        title_label = QLabel("🤖 AI音声コマンド")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2196F3;
                margin: 10px 0;
            }
        """)
        layout.addWidget(title_label)
        
        # 状態表示
        self.status_label = QLabel("準備完了")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # 音声入力ボタン
        button_layout = QHBoxLayout()
        
        self.voice_btn = QPushButton("🎤 音声入力開始")
        self.voice_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.stop_btn.setEnabled(False)
        
        button_layout.addWidget(self.voice_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # テキスト入力エリア
        text_group = QGroupBox("テキスト入力")
        text_layout = QVBoxLayout(text_group)
        
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("例: 田中商事の今月分の請求書を作成して")
        self.text_input.setStyleSheet("font-size: 14px; padding: 8px;")
        
        self.process_btn = QPushButton("処理実行")
        self.process_btn.setStyleSheet("""
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
        
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.text_input)
        input_layout.addWidget(self.process_btn)
        
        text_layout.addLayout(input_layout)
        layout.addWidget(text_group)
        
        # 応答表示エリア
        response_group = QGroupBox("AI応答")
        response_layout = QVBoxLayout(response_group)
        
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setMaximumHeight(150)
        self.response_text.setPlaceholderText("AI応答がここに表示されます...")
        self.response_text.setStyleSheet("font-size: 12px; padding: 8px;")
        
        response_layout.addWidget(self.response_text)
        layout.addWidget(response_group)
        
        # 機能有効チェック
        if not self.ai_assistant.is_enabled():
            self.setEnabled(False)
            # より詳細なステータス表示
            if not config_manager.is_ai_enabled():
                self.status_label.setText("AI機能が設定で無効化されています")
            elif not config_manager.get_ai_setting("GEMINI_API_KEY", "") and not config_manager.get_ai_setting("OPENAI_API_KEY", ""):
                self.status_label.setText("AI APIキーが設定されていません（設定→AI機能で設定してください）")
            else:
                self.status_label.setText("AI機能を初期化中です...")
            
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                    padding: 8px;
                    color: #856404;
                }
            """)
        else:
            # AI機能が有効の場合
            self.status_label.setText("AI機能: 正常動作")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 4px;
                    padding: 8px;
                    color: #155724;
                }
            """)
        
        if not SPEECH_RECOGNITION_AVAILABLE:
            self.voice_btn.setEnabled(False)
            self.voice_btn.setText("🎤 音声認識ライブラリが必要です")
        
        # 新しい音声システムとの統合
        try:
            from core.voice_system import voice_assistant
            if voice_assistant.is_recognition_available():
                # 音声アシスタントが利用可能な場合は統合
                voice_assistant.command_executed.connect(self.on_voice_command_executed)
                voice_assistant.status_changed.connect(self.on_voice_status_changed)
                voice_assistant.error_occurred.connect(self.on_voice_error)
                
                # ボタンテキスト更新
                if self.voice_btn.isEnabled():
                    self.voice_btn.setText("🎤 音声入力開始（強化版）")
                    
        except Exception as e:
            logger.error(f"音声システム統合エラー: {e}")
    
    def setup_connections(self):
        """シグナル接続"""
        self.voice_btn.clicked.connect(self.start_voice_recognition)
        self.stop_btn.clicked.connect(self.stop_voice_recognition)
        self.process_btn.clicked.connect(self.process_text_input)
        self.text_input.returnPressed.connect(self.process_text_input)
        
        # 音声認識シグナル
        self.voice_recognition.speech_recognized.connect(self.on_speech_recognized)
        self.voice_recognition.recognition_started.connect(self.on_recognition_started)
        self.voice_recognition.recognition_stopped.connect(self.on_recognition_stopped)
        self.voice_recognition.error_occurred.connect(self.on_recognition_error)
    
    def start_voice_recognition(self):
        """音声認識開始"""
        try:
            from core.voice_system import voice_assistant
            if voice_assistant.is_recognition_available():
                # 強化版音声アシスタントを使用
                voice_assistant.start_listening(continuous=False)
            else:
                # 従来の音声認識を使用
                self.voice_recognition.start_listening()
        except Exception as e:
            logger.error(f"音声認識開始エラー: {e}")
            self.voice_recognition.start_listening()
    
    def stop_voice_recognition(self):
        """音声認識停止"""
        try:
            from core.voice_system import voice_assistant
            voice_assistant.stop_listening()
        except Exception:
            pass
        self.voice_recognition.stop_listening()
    
    def on_speech_recognized(self, text: str):
        """音声認識完了"""
        self.text_input.setText(text)
        self.status_label.setText(f"認識: {text}")
        
        # 自動処理実行
        self.process_command(text)
    
    def on_recognition_started(self):
        """音声認識開始"""
        self.voice_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("🎤 音声入力中... 話してください")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e8f5e8;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 8px;
                color: #2e7d32;
            }
        """)
    
    def on_recognition_stopped(self):
        """音声認識停止"""
        self.voice_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("準備完了")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
        """)
    
    def on_recognition_error(self, error: str):
        """音声認識エラー"""
        self.voice_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText(f"エラー: {error}")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 4px;
                padding: 8px;
                color: #721c24;
            }
        """)
    
    def process_text_input(self):
        """テキスト入力処理"""
        text = self.text_input.text().strip()
        if text:
            self.process_command(text)
    
    def process_command(self, command: str):
        """コマンド処理"""
        try:
            # AI処理実行
            result = self.ai_assistant.process_natural_language_query(command)
            
            if "error" in result:
                self.response_text.setPlainText(f"エラー: {result['error']}")
                return
            
            # 結果表示
            response_text = f"操作: {result.get('action', '不明')}\n"
            response_text += f"説明: {result.get('explanation', '')}\n"
            response_text += f"信頼度: {result.get('confidence', 0):.2f}\n"
            
            if result.get('parameters'):
                response_text += f"パラメータ: {result['parameters']}"
            
            self.response_text.setPlainText(response_text)
            
            # コマンド実行シグナル発行
            action = result.get('action', '')
            parameters = result.get('parameters', {})
            
            if action and result.get('confidence', 0) > 0.5:
                self.command_recognized.emit(action, parameters)
            
        except Exception as e:
            logger.error(f"コマンド処理エラー: {e}")
            self.response_text.setPlainText(f"処理エラー: {str(e)}")
    
    def on_voice_command_executed(self, action: str, result: dict):
        """音声コマンド実行完了時の処理"""
        self.response_text.setPlainText(f"音声コマンド実行完了:\n操作: {action}\n結果: {result}")
    
    def on_voice_status_changed(self, status: str):
        """音声システム状態変更時の処理"""
        self.status_label.setText(status)
    
    def on_voice_error(self, error: str):
        """音声システムエラー時の処理"""
        self.status_label.setText(f"音声エラー: {error}")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 4px;
                padding: 8px;
                color: #721c24;
            }
        """)


class AISettingsDialog(QDialog):
    """AI設定ダイアログ"""
    
    def __init__(self, ai_assistant: AIAssistant, parent=None):
        super().__init__(parent)
        self.ai_assistant = ai_assistant
        self.setWindowTitle("AI機能設定")
        self.setModal(True)
        self.resize(500, 400)
        self.setup_ui()
        self.setup_connections()
        self.load_current_settings()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # OpenAI設定
        openai_group = QGroupBox("OpenAI API設定")
        openai_layout = QFormLayout(openai_group)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("sk-...")
        
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-4",
            "gpt-4-32k"
        ])
        
        openai_layout.addRow("APIキー:", self.api_key_edit)
        openai_layout.addRow("モデル:", self.model_combo)
        
        layout.addWidget(openai_group)
        
        # テスト
        test_group = QGroupBox("接続テスト")
        test_layout = QVBoxLayout(test_group)
        
        self.test_btn = QPushButton("接続テスト実行")
        self.test_btn.setStyleSheet("""
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
        
        self.test_result = QTextEdit()
        self.test_result.setMaximumHeight(100)
        self.test_result.setReadOnly(True)
        
        test_layout.addWidget(self.test_btn)
        test_layout.addWidget(self.test_result)
        
        layout.addWidget(test_group)
        
        # ボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("キャンセル")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def setup_connections(self):
        """シグナル接続"""
        self.test_btn.clicked.connect(self.test_connection)
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)
    
    def load_current_settings(self):
        """現在の設定読み込み"""
        self.api_key_edit.setText(self.ai_assistant.openai_api_key)
        
        index = self.model_combo.findText(self.ai_assistant.openai_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
    
    def test_connection(self):
        """接続テスト"""
        api_key = self.api_key_edit.text().strip()
        
        if not api_key:
            self.test_result.setPlainText("APIキーを入力してください。")
            return
        
        if not OPENAI_AVAILABLE:
            self.test_result.setPlainText("OpenAIライブラリがインストールされていません。")
            return
        
        try:
            # 一時的にAPIキー設定
            openai.api_key = api_key
            
            # テストリクエスト
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            self.test_result.setPlainText("✅ 接続成功: OpenAI APIに正常に接続できました。")
            
        except Exception as e:
            self.test_result.setPlainText(f"❌ 接続失敗: {str(e)}")
    
    def save_settings(self):
        """設定保存"""
        api_key = self.api_key_edit.text().strip()
        model = self.model_combo.currentText()
        
        self.ai_assistant.set_api_key(api_key)
        self.ai_assistant.openai_model = model
        self.ai_assistant.save_settings()
        
        QMessageBox.information(self, "保存完了", "AI設定を保存しました。")
        self.accept()


# グローバルAIアシスタント
ai_assistant = AIAssistant()