"""
フォームヘッダーウィジェット

フォーム上部に配置する汎用的なヘッダーコンポーネント。
音声入力ボタンとカスタマイズ可能なアクションボタン群を提供。
"""

import sys
import subprocess
import platform
from typing import List, Optional, Callable, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel,
    QSpacerItem, QSizePolicy, QToolButton, QMenu, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QThread, pyqtSlot
from PyQt6.QtGui import QIcon, QAction, QFont

# Windows音声認識API
try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False
    print("音声認識機能は利用できません。speech_recognitionをインストールしてください。")


class SpeechRecognitionThread(QThread):
    """音声認識用の別スレッド"""
    
    # 音声認識結果のシグナル
    recognized = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    started = pyqtSignal()
    finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.recognizer = None
        self.microphone = None
        self.is_listening = False
        
        # 音声認識の初期化（エラーハンドリング付き）
        if SPEECH_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()
                # マイクの初期化テスト
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            except Exception as e:
                print(f"音声認識初期化エラー: {e}")
                self.recognizer = None
                self.microphone = None
    
    def run(self):
        """音声認識を実行"""
        if not SPEECH_AVAILABLE or not self.recognizer or not self.microphone:
            self.error_occurred.emit("音声認識機能が利用できません")
            return
        
        try:
            self.started.emit()
            
            # マイクアクセスのテスト
            try:
                with self.microphone as source:
                    # 短いタイムアウトでノイズ調整
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    # 音声を聞き取る（タイムアウトを短く）
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
            except OSError as e:
                self.error_occurred.emit(f"マイクアクセスエラー: オーディオデバイスが利用できません")
                return
            except Exception as e:
                self.error_occurred.emit(f"音声取得エラー: {str(e)}")
                return
            
            # 音声をテキストに変換（日本語）
            try:
                text = self.recognizer.recognize_google(audio, language='ja-JP')
                if text and text.strip():
                    self.recognized.emit(text)
                else:
                    self.error_occurred.emit("音声を認識できませんでした")
            except sr.UnknownValueError:
                self.error_occurred.emit("音声を認識できませんでした")
            except sr.RequestError as e:
                self.error_occurred.emit(f"音声認識サービスエラー: {str(e)}")
            except Exception as e:
                self.error_occurred.emit(f"音声変換エラー: {str(e)}")
                
        except Exception as e:
            self.error_occurred.emit(f"予期しないエラー: {str(e)}")
        finally:
            self.finished.emit()


class WindowsVoiceInput:
    """Windows音声入力機能の管理クラス"""
    
    @staticmethod
    def is_windows():
        """Windowsかどうか判定"""
        return platform.system() == "Windows"
    
    @staticmethod
    def open_windows_voice_typing():
        """Windows音声入力（Win+H）を起動"""
        if not WindowsVoiceInput.is_windows():
            return False, "Windows以外では利用できません"
        
        try:
            # PowerShellを使ってWin+Hを送信
            # または音声認識を直接起動
            cmd = [
                "powershell", "-Command",
                "Add-Type -AssemblyName System.Windows.Forms; "
                "[System.Windows.Forms.SendKeys]::SendWait('^{ESC}'); "
                "Start-Sleep -Milliseconds 100; "
                "[System.Windows.Forms.SendKeys]::SendWait('#{h}');"
            ]
            subprocess.run(cmd, shell=True, check=True)
            return True, "Windows音声入力を起動しました"
        except subprocess.CalledProcessError as e:
            return False, f"音声入力起動エラー: {e}"
        except Exception as e:
            return False, f"予期しないエラー: {e}"
    
    @staticmethod
    def open_speech_recognition():
        """Windows音声認識を起動"""
        if not WindowsVoiceInput.is_windows():
            return False, "Windows以外では利用できません"
        
        try:
            # Windows音声認識アプリを起動
            subprocess.run(["SpeechRecognition.exe"], shell=True, check=False)
            return True, "Windows音声認識を起動しました"
        except Exception as e:
            # 代替手段でWin+Ctrl+Sを送信（音声認識のショートカット）
            try:
                cmd = [
                    "powershell", "-Command",
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "[System.Windows.Forms.SendKeys]::SendWait('^{LWIN}s');"
                ]
                subprocess.run(cmd, shell=True, check=True)
                return True, "Windows音声認識ショートカットを実行しました"
            except Exception as e2:
                return False, f"音声認識起動エラー: {e2}"


class ActionButton:
    """アクションボタンの定義"""
    
    def __init__(self, 
                 text: str,
                 icon: Optional[str] = None,
                 callback: Optional[Callable] = None,
                 tooltip: Optional[str] = None,
                 shortcut: Optional[str] = None,
                 menu: Optional[List[Dict[str, Any]]] = None):
        """
        Args:
            text: ボタンのテキスト
            icon: アイコンのパス（オプション）
            callback: クリック時のコールバック関数
            tooltip: ツールチップテキスト
            shortcut: キーボードショートカット
            menu: ドロップダウンメニュー項目のリスト
        """
        self.text = text
        self.icon = icon
        self.callback = callback
        self.tooltip = tooltip
        self.shortcut = shortcut
        self.menu = menu


class FormHeaderWidget(QWidget):
    """フォームヘッダーウィジェット"""
    
    # シグナル定義
    voice_input_received = pyqtSignal(str)  # 音声入力を受信
    action_triggered = pyqtSignal(str)      # アクションボタンがクリックされた
    
    def __init__(self, 
                 title: Optional[str] = None,
                 actions: Optional[List[ActionButton]] = None,
                 enable_voice_input: bool = True,
                 parent: Optional[QWidget] = None):
        """
        Args:
            title: ヘッダーのタイトル（オプション）
            actions: アクションボタンのリスト
            enable_voice_input: 音声入力ボタンを表示するか
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.title = title
        self.actions = actions or []
        self.enable_voice_input = enable_voice_input
        
        # 音声認識スレッド
        self.speech_thread = None
        
        self._init_ui()
        self._apply_styles()
    
    def _init_ui(self):
        """UIを初期化"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # タイトルラベル（オプション）
        if self.title:
            title_label = QLabel(self.title)
            title_label.setObjectName("headerTitle")
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            title_label.setFont(font)
            layout.addWidget(title_label)
        
        # スペーサー（左寄せ用）
        layout.addSpacerItem(
            QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        
        # 音声入力ボタン（ドロップダウンメニュー付き）
        if self.enable_voice_input:
            self.voice_button = QToolButton()
            self.voice_button.setObjectName("voiceInputButton")
            self.voice_button.setText("🎤 音声入力")
            self.voice_button.setMinimumHeight(32)
            self.voice_button.setMaximumWidth(150)
            self.voice_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
            
            # 音声入力メニュー作成
            voice_menu = QMenu(self.voice_button)
            
            # Windows音声入力オプション
            if WindowsVoiceInput.is_windows():
                win_voice_action = QAction("🪟 Windows音声入力 (Win+H)", voice_menu)
                win_voice_action.setToolTip("Windowsの音声入力機能を起動します")
                win_voice_action.triggered.connect(self._on_windows_voice_input)
                voice_menu.addAction(win_voice_action)
                
                voice_menu.addSeparator()
            
            # アプリ内音声認識オプション
            if SPEECH_AVAILABLE:
                app_voice_action = QAction("🎙️ アプリ内音声認識", voice_menu)
                app_voice_action.setToolTip("アプリ内蔵の音声認識機能を使用")
                app_voice_action.triggered.connect(self._on_voice_input_clicked)
                voice_menu.addAction(app_voice_action)
            
            # テキスト入力フォールバック
            text_input_action = QAction("⌨️ テキスト入力", voice_menu)
            text_input_action.setToolTip("キーボードでコマンドを入力")
            text_input_action.triggered.connect(self._on_text_input_fallback)
            voice_menu.addAction(text_input_action)
            
            self.voice_button.setMenu(voice_menu)
            
            # デフォルトアクション設定（Win+Hを優先）
            if WindowsVoiceInput.is_windows():
                self.voice_button.clicked.connect(self._on_windows_voice_input)
                self.voice_button.setToolTip("Windows音声入力 (Win+H) を起動 ▼メニューで他の方法も選択可能")
                self.voice_button.setShortcut("Ctrl+H")
            elif SPEECH_AVAILABLE:
                self.voice_button.clicked.connect(self._on_voice_input_clicked)
                self.voice_button.setToolTip("アプリ内音声認識を使用 (Ctrl+Shift+V)")
                self.voice_button.setShortcut("Ctrl+Shift+V")
            else:
                self.voice_button.clicked.connect(self._on_text_input_fallback)
                self.voice_button.setToolTip("テキスト入力モード (Ctrl+Shift+V)")
                self.voice_button.setShortcut("Ctrl+Shift+V")
                self.voice_button.setText("📝 テキスト入力")
            
            layout.addWidget(self.voice_button)
        
        # アクションボタン群
        for action in self.actions:
            button = self._create_action_button(action)
            layout.addWidget(button)
    
    def _create_action_button(self, action: ActionButton) -> QPushButton:
        """アクションボタンを作成"""
        if action.menu:
            # メニュー付きボタン
            button = QToolButton()
            button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
            
            menu = QMenu(button)
            for item in action.menu:
                menu_action = QAction(item.get('text', ''), menu)
                if 'icon' in item:
                    menu_action.setIcon(QIcon(item['icon']))
                if 'callback' in item:
                    menu_action.triggered.connect(item['callback'])
                menu.addAction(menu_action)
            
            button.setMenu(menu)
        else:
            # 通常のボタン
            button = QPushButton()
        
        button.setText(action.text)
        button.setObjectName("actionButton")
        button.setMinimumHeight(32)
        
        if action.icon:
            button.setIcon(QIcon(action.icon))
            button.setIconSize(QSize(20, 20))
        
        if action.tooltip:
            button.setToolTip(action.tooltip)
        
        if action.shortcut:
            button.setShortcut(action.shortcut)
        
        if action.callback:
            button.clicked.connect(action.callback)
        else:
            button.clicked.connect(lambda: self.action_triggered.emit(action.text))
        
        return button
    
    def _apply_styles(self):
        """スタイルを適用"""
        self.setStyleSheet("""
            FormHeaderWidget {
                background-color: #f5f5f5;
                border-bottom: 1px solid #ddd;
                min-height: 50px;
            }
            
            #headerTitle {
                color: #333;
                padding: 0 10px;
            }
            
            #voiceInputButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            
            #voiceInputButton:hover {
                background-color: #45a049;
            }
            
            #voiceInputButton:pressed {
                background-color: #3d8b40;
            }
            
            #voiceInputButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            
            #voiceInputButton::menu-indicator {
                image: none;
                width: 10px;
                subcontrol-position: right center;
                subcontrol-origin: padding;
                right: 4px;
            }
            
            #actionButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            
            #actionButton:hover {
                background-color: #1976D2;
            }
            
            #actionButton:pressed {
                background-color: #1565C0;
            }
            
            QToolButton::menu-indicator {
                image: none;
                width: 10px;
                subcontrol-position: right center;
                subcontrol-origin: padding;
                right: 4px;
            }
        """)
    
    @pyqtSlot()
    def _on_voice_input_clicked(self):
        """音声入力ボタンがクリックされた時"""
        if not SPEECH_AVAILABLE:
            self.voice_input_received.emit("[エラー] 音声認識機能が利用できません")
            return
        
        # 既に音声認識中の場合は停止
        if self.speech_thread and self.speech_thread.isRunning():
            self.speech_thread.terminate()
            self.speech_thread.wait(1000)  # 1秒待機
            return
        
        # 音声認識スレッドを開始（エラーハンドリング付き）
        try:
            self.speech_thread = SpeechRecognitionThread()
            
            # シグナル接続
            self.speech_thread.recognized.connect(self._on_speech_recognized)
            self.speech_thread.error_occurred.connect(self._on_speech_error)
            self.speech_thread.started.connect(self._on_speech_started)
            self.speech_thread.finished.connect(self._on_speech_finished)
            
            # スレッド開始
            self.speech_thread.start()
            
        except Exception as e:
            self.voice_input_received.emit(f"[エラー] 音声認識の開始に失敗: {str(e)}")
    
    @pyqtSlot()
    def _on_windows_voice_input(self):
        """Windows音声入力（Win+H）を起動"""
        success, message = WindowsVoiceInput.open_windows_voice_typing()
        if success:
            self.voice_input_received.emit(f"[システム] {message}")
            # 音声入力が完了するまでのガイダンス
            self.voice_input_received.emit("[ガイド] Windows音声入力が起動しました。話したい内容を発話してください。")
        else:
            self.voice_input_received.emit(f"[エラー] {message}")
    
    @pyqtSlot()
    def _on_windows_speech_recognition(self):
        """Windows音声認識を起動"""
        success, message = WindowsVoiceInput.open_speech_recognition()
        if success:
            self.voice_input_received.emit(f"[システム] {message}")
        else:
            self.voice_input_received.emit(f"[エラー] {message}")
    
    @pyqtSlot(str)
    def _on_speech_recognized(self, text: str):
        """音声が認識された時"""
        self.voice_input_received.emit(text)
    
    @pyqtSlot(str)
    def _on_speech_error(self, error_message: str):
        """音声認識エラーが発生した時"""
        self.voice_input_received.emit(f"[エラー] {error_message}")
    
    @pyqtSlot()
    def _on_speech_started(self):
        """音声認識が開始された時"""
        if hasattr(self, 'voice_button'):
            self.voice_button.setEnabled(False)
            self.voice_button.setText("聞き取り中...")
    
    @pyqtSlot()
    def _on_speech_finished(self):
        """音声認識が終了した時"""
        if hasattr(self, 'voice_button'):
            self.voice_button.setEnabled(True)
            self.voice_button.setText("音声入力")
    
    def add_action(self, action: ActionButton):
        """アクションボタンを追加"""
        self.actions.append(action)
        button = self._create_action_button(action)
        # レイアウトの最後から2番目に挿入（スペーサーの前）
        layout = self.layout()
        layout.insertWidget(layout.count() - 1, button)
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        if self.speech_thread and self.speech_thread.isRunning():
            self.speech_thread.terminate()
            self.speech_thread.wait(1000)  # 1秒待機
            self.speech_thread = None
    
    def __del__(self):
        """デストラクタ"""
        self.cleanup()
    
    @pyqtSlot()
    def _on_text_input_fallback(self):
        """音声認識が利用できない場合のテキスト入力フォールバック"""
        text, ok = QInputDialog.getText(
            self, 
            "音声コマンド入力", 
            "音声コマンドをテキストで入力してください:\n\n例: 新規取引先, 検索, 在庫確認, エクスポート"
        )
        
        if ok and text.strip():
            self.voice_input_received.emit(text.strip())
    
    def remove_action(self, text: str):
        """指定されたテキストのアクションボタンを削除"""
        for i, action in enumerate(self.actions):
            if action.text == text:
                self.actions.pop(i)
                # UIからも削除
                layout = self.layout()
                for j in range(layout.count()):
                    widget = layout.itemAt(j).widget()
                    if widget and hasattr(widget, 'text') and widget.text() == text:
                        layout.removeWidget(widget)
                        widget.deleteLater()
                        break
                break
    
    def set_title(self, title: str):
        """タイトルを設定"""
        self.title = title
        # タイトルラベルを更新または作成
        layout = self.layout()
        title_label = None
        
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget and widget.objectName() == "headerTitle":
                title_label = widget
                break
        
        if title_label:
            title_label.setText(title)
        else:
            # 新しくタイトルラベルを作成
            title_label = QLabel(title)
            title_label.setObjectName("headerTitle")
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            title_label.setFont(font)
            layout.insertWidget(0, title_label)
    
    def set_voice_input_enabled(self, enabled: bool):
        """音声入力ボタンの有効/無効を設定"""
        if hasattr(self, 'voice_button'):
            self.voice_button.setEnabled(enabled and SPEECH_AVAILABLE)


# 使用例
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QTextEdit
    
    app = QApplication(sys.argv)
    
    # メインウィンドウ
    window = QMainWindow()
    window.setWindowTitle("FormHeaderWidget デモ")
    window.setGeometry(100, 100, 800, 600)
    
    # 中央ウィジェット
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    # レイアウト
    layout = QVBoxLayout(central_widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    
    # アクションボタンの定義
    actions = [
        ActionButton(
            text="新規作成",
            icon="",  # アイコンパス
            callback=lambda: print("新規作成がクリックされました"),
            tooltip="新しいレコードを作成 (Ctrl+N)",
            shortcut="Ctrl+N"
        ),
        ActionButton(
            text="保存",
            callback=lambda: print("保存がクリックされました"),
            tooltip="変更を保存 (Ctrl+S)",
            shortcut="Ctrl+S"
        ),
        ActionButton(
            text="エクスポート",
            menu=[
                {"text": "CSVエクスポート", "callback": lambda: print("CSV エクスポート")},
                {"text": "Excelエクスポート", "callback": lambda: print("Excel エクスポート")},
                {"text": "PDFエクスポート", "callback": lambda: print("PDF エクスポート")},
            ]
        ),
    ]
    
    # フォームヘッダーウィジェット
    header = FormHeaderWidget(
        title="取引先管理",
        actions=actions,
        enable_voice_input=True
    )
    
    # 音声入力を受信した時の処理
    def on_voice_input(text):
        text_edit.append(f"音声入力: {text}")
    
    header.voice_input_received.connect(on_voice_input)
    
    # アクションがトリガーされた時の処理
    def on_action(action_name):
        text_edit.append(f"アクション: {action_name}")
    
    header.action_triggered.connect(on_action)
    
    # レイアウトに追加
    layout.addWidget(header)
    
    # テキストエディタ（デモ用）
    text_edit = QTextEdit()
    text_edit.setPlaceholderText("ここに音声入力やアクションの結果が表示されます...")
    layout.addWidget(text_edit)
    
    # ウィンドウを表示
    window.show()
    
    sys.exit(app.exec())