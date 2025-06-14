#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v4.0 - 音声認識・合成システム
音声コマンド機能と読み上げ機能の完全実装
"""

import logging
import json
import threading
import queue
import time
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import re

from PyQt6.QtCore import QThread, pyqtSignal, QObject, QTimer, QSettings
from PyQt6.QtWidgets import QMessageBox

# 音声認識ライブラリ
try:
    import speech_recognition as sr
    import pyaudio
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

# 音声合成ライブラリ
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# Windows SAPI (フォールバック)
try:
    import win32com.client
    WINDOWS_SAPI_AVAILABLE = True
except ImportError:
    WINDOWS_SAPI_AVAILABLE = False

from core.config_manager import config_manager

logger = logging.getLogger(__name__)


class VoiceCommand:
    """音声コマンドクラス"""
    
    def __init__(self, pattern: str, action: str, description: str, parameters: Dict[str, Any] = None):
        self.pattern = pattern  # 正規表現パターン
        self.action = action    # 実行するアクション
        self.description = description  # コマンド説明
        self.parameters = parameters or {}


class VoiceCommandRegistry:
    """音声コマンド登録・管理クラス"""
    
    def __init__(self):
        self.commands: List[VoiceCommand] = []
        self.setup_default_commands()
    
    def setup_default_commands(self):
        """デフォルト音声コマンド設定"""
        default_commands = [
            # 基本操作
            VoiceCommand(r"ダッシュボード(を)?(表示|開いて|見せて)", "show_dashboard", "ダッシュボードを表示"),
            VoiceCommand(r"設定(を)?(開いて|表示)", "show_settings", "設定画面を表示"),
            VoiceCommand(r"ヘルプ(を)?(開いて|表示)", "show_help", "ヘルプを表示"),
            
            # 取引先管理
            VoiceCommand(r"取引先(を)?(検索|探して|調べて)", "search_customer", "取引先を検索"),
            VoiceCommand(r"顧客(を)?(検索|探して|調べて)", "search_customer", "顧客を検索"),
            VoiceCommand(r"(.+)(の|という)取引先(を)?(検索|探して)", "search_customer_by_name", "指定取引先を検索", {"name_group": 1}),
            VoiceCommand(r"新しい取引先(を)?(登録|追加)", "add_customer", "新規取引先を登録"),
            
            # 商品管理
            VoiceCommand(r"商品(を)?(検索|探して|調べて)", "search_product", "商品を検索"),
            VoiceCommand(r"(.+)(の|という)商品(を)?(検索|探して)", "search_product_by_name", "指定商品を検索", {"name_group": 1}),
            VoiceCommand(r"在庫(を)?(確認|チェック)", "check_inventory", "在庫を確認"),
            VoiceCommand(r"在庫管理(を)?(開いて|表示)", "show_inventory", "在庫管理画面を表示"),
            
            # 貸出・返却
            VoiceCommand(r"貸出(を)?(登録|追加|処理)", "create_loan", "新規貸出を登録"),
            VoiceCommand(r"返却(を)?(登録|処理)", "process_return", "返却処理"),
            VoiceCommand(r"貸出履歴(を)?(確認|表示)", "show_loan_history", "貸出履歴を表示"),
            
            # 請求書
            VoiceCommand(r"請求書(を)?(作成|生成)", "create_invoice", "請求書を作成"),
            VoiceCommand(r"(.+)(の|という|への)請求書(を)?(作成|生成)", "create_invoice_for_customer", "指定顧客の請求書を作成", {"customer_group": 1}),
            VoiceCommand(r"今月(の)?請求書(を)?(作成|生成)", "create_monthly_invoice", "今月の請求書を作成"),
            
            # 分析・レポート
            VoiceCommand(r"売上(を)?(分析|確認)", "analyze_sales", "売上分析を表示"),
            VoiceCommand(r"今月(の)?売上(を)?(分析|確認)", "analyze_monthly_sales", "今月の売上分析"),
            VoiceCommand(r"レポート(を)?(表示|生成)", "generate_report", "レポートを生成"),
            VoiceCommand(r"統計(を)?(表示|確認)", "show_statistics", "統計情報を表示"),
            
            # システム操作
            VoiceCommand(r"バックアップ(を)?(作成|実行)", "create_backup", "バックアップを作成"),
            VoiceCommand(r"データ(を)?(エクスポート|出力)", "export_data", "データをエクスポート"),
            VoiceCommand(r"最適化(を)?実行", "optimize_database", "データベースを最適化"),
            
            # AI機能
            VoiceCommand(r"AI(チャット|を)?(開いて|表示)", "show_ai_chat", "AIチャットを表示"),
            VoiceCommand(r"AI(に)?(質問|聞いて)", "start_ai_conversation", "AI会話を開始"),
            
            # 終了・キャンセル
            VoiceCommand(r"キャンセル", "cancel", "現在の操作をキャンセル"),
            VoiceCommand(r"終了|閉じて", "close", "アプリケーションを終了"),
            VoiceCommand(r"停止|やめて", "stop", "音声認識を停止"),
        ]
        
        self.commands.extend(default_commands)
    
    def register_command(self, command: VoiceCommand):
        """コマンド登録"""
        self.commands.append(command)
    
    def match_command(self, text: str) -> Optional[Dict[str, Any]]:
        """音声テキストからコマンドマッチング"""
        text = text.strip()
        
        for command in self.commands:
            try:
                match = re.search(command.pattern, text, re.IGNORECASE)
                if match:
                    result = {
                        "action": command.action,
                        "description": command.description,
                        "original_text": text,
                        "parameters": command.parameters.copy()
                    }
                    
                    # グループ抽出
                    if command.parameters.get("name_group"):
                        name_group = command.parameters["name_group"]
                        if match.group(name_group):
                            result["parameters"]["name"] = match.group(name_group).strip()
                    
                    if command.parameters.get("customer_group"):
                        customer_group = command.parameters["customer_group"]
                        if match.group(customer_group):
                            result["parameters"]["customer_name"] = match.group(customer_group).strip()
                    
                    return result
                    
            except Exception as e:
                logger.error(f"コマンドマッチングエラー ({command.pattern}): {e}")
        
        return None
    
    def get_available_commands(self) -> List[Dict[str, str]]:
        """利用可能なコマンド一覧取得"""
        return [
            {
                "action": cmd.action,
                "description": cmd.description,
                "pattern": cmd.pattern
            }
            for cmd in self.commands
        ]


class TextToSpeechEngine(QObject):
    """音声合成エンジン"""
    
    speech_started = pyqtSignal()
    speech_finished = pyqtSignal()
    speech_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.engine = None
        self.sapi_voice = None
        self.enabled = False
        self.speaking = False
        self.speech_queue = queue.Queue()
        self.worker_thread = None
        
        self.initialize_engine()
        
        if self.enabled:
            self.start_worker_thread()
    
    def initialize_engine(self):
        """音声合成エンジン初期化"""
        try:
            # pyttsx3を優先的に使用
            if TTS_AVAILABLE:
                self.engine = pyttsx3.init()
                
                # 日本語音声設定
                voices = self.engine.getProperty('voices')
                for voice in voices:
                    if 'japanese' in voice.name.lower() or 'ja' in voice.id.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
                
                # 音声設定
                self.engine.setProperty('rate', 150)  # 話速
                self.engine.setProperty('volume', 0.8)  # 音量
                
                self.enabled = True
                logger.info("pyttsx3音声合成エンジン初期化完了")
                return
                
        except Exception as e:
            logger.error(f"pyttsx3初期化エラー: {e}")
        
        try:
            # Windows SAPIフォールバック
            if WINDOWS_SAPI_AVAILABLE:
                self.sapi_voice = win32com.client.Dispatch("SAPI.SpVoice")
                
                # 日本語音声を検索
                voices = self.sapi_voice.GetVoices()
                for i in range(voices.Count):
                    voice = voices.Item(i)
                    if 'japanese' in voice.GetDescription().lower():
                        self.sapi_voice.Voice = voice
                        break
                
                self.enabled = True
                logger.info("Windows SAPI音声合成エンジン初期化完了")
                return
                
        except Exception as e:
            logger.error(f"Windows SAPI初期化エラー: {e}")
        
        logger.warning("音声合成エンジンを初期化できませんでした")
    
    def start_worker_thread(self):
        """ワーカースレッド開始"""
        self.worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.worker_thread.start()
    
    def _speech_worker(self):
        """音声合成ワーカー"""
        while True:
            try:
                text = self.speech_queue.get(timeout=1)
                if text is None:  # 終了シグナル
                    break
                
                self.speaking = True
                self.speech_started.emit()
                
                if self.engine:
                    # pyttsx3使用
                    self.engine.say(text)
                    self.engine.runAndWait()
                elif self.sapi_voice:
                    # Windows SAPI使用
                    self.sapi_voice.Speak(text)
                
                self.speaking = False
                self.speech_finished.emit()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.speaking = False
                self.speech_error.emit(str(e))
                logger.error(f"音声合成エラー: {e}")
    
    def speak(self, text: str, priority: bool = False):
        """テキスト読み上げ"""
        if not self.enabled:
            return
        
        if not config_manager.get_ai_setting("TTS_ENABLED", False):
            return
        
        try:
            # 優先度が高い場合は既存のキューをクリア
            if priority:
                with self.speech_queue.mutex:
                    self.speech_queue.queue.clear()
            
            self.speech_queue.put(text)
            
        except Exception as e:
            logger.error(f"音声合成キューイングエラー: {e}")
    
    def stop_speaking(self):
        """読み上げ停止"""
        try:
            # キューをクリア
            with self.speech_queue.mutex:
                self.speech_queue.queue.clear()
            
            if self.engine:
                self.engine.stop()
            
            self.speaking = False
            
        except Exception as e:
            logger.error(f"音声合成停止エラー: {e}")
    
    def is_speaking(self) -> bool:
        """読み上げ中かどうか"""
        return self.speaking
    
    def is_enabled(self) -> bool:
        """音声合成が有効かどうか"""
        return self.enabled and config_manager.get_ai_setting("TTS_ENABLED", False)


class EnhancedVoiceRecognitionThread(QThread):
    """強化版音声認識スレッド"""
    
    # シグナル
    speech_recognized = pyqtSignal(str)  # 認識されたテキスト
    command_recognized = pyqtSignal(dict)  # 認識されたコマンド
    recognition_started = pyqtSignal()
    recognition_stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.recognizer = None
        self.microphone = None
        self.is_listening = False
        self.is_continuous = False
        self.command_registry = VoiceCommandRegistry()
        self.settings = QSettings("BusinessSystem", "VoiceRecognition")
        
        # 認識設定
        self.language = "ja-JP"
        self.energy_threshold = 4000
        self.phrase_timeout = 1.0
        self.pause_threshold = 0.8
        
        self.load_settings()
        self.initialize_recognition()
    
    def load_settings(self):
        """設定読み込み"""
        try:
            self.language = self.settings.value("language", "ja-JP")
            self.energy_threshold = self.settings.value("energy_threshold", 4000, int)
            self.phrase_timeout = self.settings.value("phrase_timeout", 1.0, float)
            self.pause_threshold = self.settings.value("pause_threshold", 0.8, float)
        except Exception as e:
            logger.error(f"音声認識設定読み込みエラー: {e}")
    
    def save_settings(self):
        """設定保存"""
        try:
            self.settings.setValue("language", self.language)
            self.settings.setValue("energy_threshold", self.energy_threshold)
            self.settings.setValue("phrase_timeout", self.phrase_timeout)
            self.settings.setValue("pause_threshold", self.pause_threshold)
        except Exception as e:
            logger.error(f"音声認識設定保存エラー: {e}")
    
    def initialize_recognition(self):
        """音声認識初期化"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.warning("音声認識ライブラリが利用できません")
            return
        
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            
            # マイク設定
            with self.microphone as source:
                logger.info("マイクの環境ノイズを調整中...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            # 認識設定
            self.recognizer.energy_threshold = self.energy_threshold
            self.recognizer.pause_threshold = self.pause_threshold
            self.recognizer.phrase_threshold = 0.3
            self.recognizer.non_speaking_duration = 0.8
            
            logger.info("音声認識エンジン初期化完了")
            
        except Exception as e:
            logger.error(f"音声認識初期化エラー: {e}")
            self.recognizer = None
    
    def start_listening(self, continuous: bool = False):
        """音声認識開始"""
        if not self.recognizer:
            self.error_occurred.emit("音声認識エンジンが初期化されていません")
            return
        
        if not config_manager.get_ai_setting("VOICE_RECOGNITION_ENABLED", False):
            self.error_occurred.emit("音声認識が設定で無効化されています")
            return
        
        if not self.is_listening:
            self.is_listening = True
            self.is_continuous = continuous
            self.start()
    
    def stop_listening(self):
        """音声認識停止"""
        self.is_listening = False
        self.is_continuous = False
    
    def run(self):
        """音声認識スレッド実行"""
        if not self.recognizer:
            self.error_occurred.emit("音声認識が利用できません")
            return
        
        self.recognition_started.emit()
        self.status_changed.emit("音声認識を開始しました")
        
        try:
            while self.is_listening:
                try:
                    with self.microphone as source:
                        self.status_changed.emit("音声入力待機中...")
                        
                        # 音声取得
                        if self.is_continuous:
                            audio = self.recognizer.listen(
                                source, 
                                timeout=1, 
                                phrase_time_limit=None
                            )
                        else:
                            audio = self.recognizer.listen(
                                source, 
                                timeout=1, 
                                phrase_time_limit=5
                            )
                    
                    self.status_changed.emit("音声を認識中...")
                    
                    # Google音声認識
                    text = self.recognizer.recognize_google(audio, language=self.language)
                    
                    if text:
                        logger.info(f"音声認識結果: {text}")
                        self.speech_recognized.emit(text)
                        
                        # コマンドマッチング
                        command = self.command_registry.match_command(text)
                        if command:
                            logger.info(f"音声コマンド認識: {command}")
                            self.command_recognized.emit(command)
                        
                        # 継続モードでない場合は停止
                        if not self.is_continuous:
                            break
                
                except sr.WaitTimeoutError:
                    # タイムアウトは継続
                    if not self.is_listening:
                        break
                    continue
                    
                except sr.UnknownValueError:
                    # 音声が認識できない場合は継続
                    self.status_changed.emit("音声を認識できませんでした")
                    if not self.is_continuous:
                        time.sleep(0.5)
                    continue
                    
                except sr.RequestError as e:
                    self.error_occurred.emit(f"音声認識サービスエラー: {e}")
                    break
                    
        except Exception as e:
            self.error_occurred.emit(f"音声認識エラー: {e}")
            logger.error(f"音声認識実行エラー: {e}")
        
        finally:
            self.is_listening = False
            self.recognition_stopped.emit()
            self.status_changed.emit("音声認識を停止しました")
    
    def is_available(self) -> bool:
        """音声認識が利用可能かどうか"""
        return (SPEECH_RECOGNITION_AVAILABLE and 
                self.recognizer is not None and
                config_manager.get_ai_setting("VOICE_RECOGNITION_ENABLED", False))
    
    def get_available_commands(self) -> List[Dict[str, str]]:
        """利用可能なコマンド一覧取得"""
        return self.command_registry.get_available_commands()


class VoiceAssistant(QObject):
    """音声アシスタント統合クラス"""
    
    # シグナル
    command_executed = pyqtSignal(str, dict)  # action, result
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 音声認識
        self.voice_recognition = EnhancedVoiceRecognitionThread()
        self.voice_recognition.speech_recognized.connect(self.on_speech_recognized)
        self.voice_recognition.command_recognized.connect(self.on_command_recognized)
        self.voice_recognition.error_occurred.connect(self.error_occurred.emit)
        self.voice_recognition.status_changed.connect(self.status_changed.emit)
        
        # 音声合成
        self.tts_engine = TextToSpeechEngine()
        
        # コマンドハンドラー
        self.command_handlers: Dict[str, Callable] = {}
        
        logger.info("音声アシスタント初期化完了")
    
    def register_command_handler(self, action: str, handler: Callable):
        """コマンドハンドラー登録"""
        self.command_handlers[action] = handler
    
    def start_listening(self, continuous: bool = False):
        """音声認識開始"""
        if self.voice_recognition.is_available():
            self.voice_recognition.start_listening(continuous)
            self.speak("音声入力を開始します。何かお手伝いできることはありますか？")
        else:
            self.error_occurred.emit("音声認識が利用できません")
    
    def stop_listening(self):
        """音声認識停止"""
        self.voice_recognition.stop_listening()
        self.speak("音声入力を停止しました")
    
    def speak(self, text: str, priority: bool = False):
        """テキスト読み上げ"""
        self.tts_engine.speak(text, priority)
    
    def stop_speaking(self):
        """読み上げ停止"""
        self.tts_engine.stop_speaking()
    
    def on_speech_recognized(self, text: str):
        """音声認識時の処理"""
        self.status_changed.emit(f"音声認識: {text}")
    
    def on_command_recognized(self, command: Dict[str, Any]):
        """コマンド認識時の処理"""
        action = command.get("action")
        description = command.get("description", "")
        
        # 音声フィードバック
        self.speak(f"{description}を実行します")
        
        # コマンドハンドラー実行
        if action in self.command_handlers:
            try:
                result = self.command_handlers[action](command)
                self.command_executed.emit(action, result or {})
            except Exception as e:
                error_msg = f"コマンド実行エラー: {str(e)}"
                self.error_occurred.emit(error_msg)
                self.speak("申し訳ございません。コマンドの実行に失敗しました。")
        else:
            self.error_occurred.emit(f"未対応のコマンド: {action}")
            self.speak("申し訳ございません。そのコマンドは対応していません。")
    
    def is_recognition_available(self) -> bool:
        """音声認識が利用可能かどうか"""
        return self.voice_recognition.is_available()
    
    def is_tts_available(self) -> bool:
        """音声合成が利用可能かどうか"""
        return self.tts_engine.is_enabled()
    
    def get_available_commands(self) -> List[Dict[str, str]]:
        """利用可能なコマンド一覧取得"""
        return self.voice_recognition.get_available_commands()


# グローバル音声アシスタント
voice_assistant = VoiceAssistant()