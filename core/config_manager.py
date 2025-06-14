"""
設定管理システム
JSON ベースの設定ファイル管理とリアルタイム設定変更対応
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal


class ConfigManager(QObject):
    """設定管理クラス"""
    
    # 設定変更時のシグナル
    setting_changed = pyqtSignal(str, object)  # key, value
    theme_changed = pyqtSignal(str)  # theme_name
    
    def __init__(self, config_dir: str = None):
        super().__init__()
        
        # ポータブル対応の設定ディレクトリ
        if config_dir is None:
            if getattr(sys, 'frozen', False):
                # PyInstallerでビルドされた場合はEXEと同じディレクトリ
                app_dir = os.path.dirname(sys.executable)
                self.config_dir = Path(app_dir) / "config"
            else:
                # 開発環境の場合はプロジェクト内
                self.config_dir = Path("config")
        else:
            self.config_dir = Path(config_dir)
        
        # ディレクトリ作成
        self.config_dir.mkdir(exist_ok=True)
        
        self.settings_file = self.config_dir / "settings.json"
        self.themes_file = self.config_dir / "themes.json"
        self.ai_settings_file = self.config_dir / "ai_settings.env"
        
        self._settings = {}
        self._themes = {}
        self._ai_settings = {}
        self._current_theme = "light"
        
        self.load_all()
    
    def load_all(self):
        """すべての設定を読み込み"""
        self.load_settings()
        self.load_themes()
        self.load_ai_settings()
    
    def load_settings(self):
        """設定ファイルを読み込み"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
            else:
                self._settings = self._get_default_settings()
                self.save_settings()
        except Exception as e:
            print(f"設定ファイル読み込みエラー: {e}")
            self._settings = self._get_default_settings()
    
    def load_themes(self):
        """テーマファイルを読み込み"""
        try:
            if self.themes_file.exists():
                with open(self.themes_file, 'r', encoding='utf-8') as f:
                    self._themes = json.load(f)
            else:
                self._themes = self._get_default_themes()
                self.save_themes()
        except Exception as e:
            print(f"テーマファイル読み込みエラー: {e}")
            self._themes = self._get_default_themes()
    
    def load_ai_settings(self):
        """AI設定ファイル(.env)を読み込み"""
        try:
            if self.ai_settings_file.exists():
                self._ai_settings = {}
                with open(self.ai_settings_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            # 値の前後の空白を削除し、trueやfalseを適切に変換
                            value = value.strip()
                            if value.lower() == 'true':
                                value = True
                            elif value.lower() == 'false':
                                value = False
                            self._ai_settings[key.strip()] = value
            else:
                self._ai_settings = self._get_default_ai_settings()
                self.save_ai_settings()
        except Exception as e:
            print(f"AI設定ファイル読み込みエラー: {e}")
            self._ai_settings = self._get_default_ai_settings()
    
    def save_ai_settings(self):
        """AI設定ファイル(.env)を保存"""
        try:
            # ディレクトリの作成（権限エラー対応）
            try:
                self.config_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                print(f"権限エラー: {self.config_dir} への書き込み権限がありません")
                return
            except Exception as e:
                print(f"ディレクトリ作成エラー: {e}")
                return
            
            # ファイルの書き込み（権限エラー対応）
            try:
                with open(self.ai_settings_file, 'w', encoding='utf-8') as f:
                    f.write("# 業務支援システム v4.0 AI設定\n\n")
                    for key, value in self._ai_settings.items():
                        if isinstance(value, bool):
                            value = str(value).lower()
                        elif value is None:
                            value = ""
                        f.write(f"{key}={value}\n")
            except PermissionError:
                print(f"権限エラー: {self.ai_settings_file} への書き込み権限がありません")
                return
            except Exception as e:
                print(f"ファイル書き込みエラー: {e}")
                return
                
        except Exception as e:
            print(f"AI設定ファイル保存の重大なエラー: {e}")
    
    def _get_default_ai_settings(self) -> Dict[str, Any]:
        """デフォルトAI設定を取得"""
        return {
            "AI_ENABLED": True,
            "OPENAI_API_KEY": "",
            "GEMINI_API_KEY": "",
            "DATABASE_ENABLED": True,
            "PDF_EXPORT_ENABLED": True,
            "EXCEL_EXPORT_ENABLED": True,
            "TTS_ENABLED": False,
            "VOICE_RECOGNITION_ENABLED": False,
            "ACCESSIBILITY_FONT_SIZE": 14,
            "ACCESSIBILITY_HIGH_CONTRAST": False
        }
    
    def get_ai_setting(self, key: str, default: Any = None) -> Any:
        """AI設定値を取得"""
        return self._ai_settings.get(key, default)
    
    def set_ai_setting(self, key: str, value: Any):
        """AI設定値を設定"""
        try:
            self._ai_settings[key] = value
            self.save_ai_settings()
            self.setting_changed.emit(f"ai.{key}", value)
        except Exception as e:
            print(f"AI設定値設定エラー ({key}): {e}")
    
    def is_ai_enabled(self) -> bool:
        """AI機能が有効かどうかを確認"""
        return self.get_ai_setting("AI_ENABLED", False)
    
    def save_settings(self):
        """設定ファイルを保存"""
        try:
            # ディレクトリの作成（権限エラー対応）
            try:
                self.config_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                print(f"権限エラー: {self.config_dir} への書き込み権限がありません")
                return
            except Exception as e:
                print(f"ディレクトリ作成エラー: {e}")
                return
            
            # ファイルの書き込み（権限エラー対応）
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(self._settings, f, indent=2, ensure_ascii=False)
            except PermissionError:
                print(f"権限エラー: {self.settings_file} への書き込み権限がありません")
                return
            except Exception as e:
                print(f"ファイル書き込みエラー: {e}")
                return
                
        except Exception as e:
            print(f"設定ファイル保存の重大なエラー: {e}")
    
    def save_themes(self):
        """テーマファイルを保存"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.themes_file, 'w', encoding='utf-8') as f:
                json.dump(self._themes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"テーマファイル保存エラー: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        keys = key.split('.')
        value = self._settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """設定値を設定"""
        keys = key.split('.')
        current = self._settings
        
        # ネストした辞書を作成
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # 値を設定
        current[keys[-1]] = value
        
        # 設定を保存
        self.save_settings()
        
        # シグナルを発信
        self.setting_changed.emit(key, value)
    
    def get_theme(self, theme_name: Optional[str] = None) -> Dict[str, Any]:
        """テーマ情報を取得"""
        if theme_name is None:
            theme_name = self._current_theme
        
        return self._themes.get(theme_name, self._themes.get("light", {}))
    
    def set_theme(self, theme_name: str):
        """テーマを切り替え"""
        if theme_name in self._themes:
            self._current_theme = theme_name
            self.set("app.theme", theme_name)
            self.theme_changed.emit(theme_name)
    
    def get_available_themes(self) -> list:
        """利用可能なテーマ一覧を取得"""
        return list(self._themes.keys())
    
    def add_custom_theme(self, name: str, theme_data: Dict[str, Any]):
        """カスタムテーマを追加"""
        self._themes[name] = theme_data
        self.save_themes()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """デフォルト設定を取得"""
        return {
            "app": {
                "name": "業務支援システム v3.0",
                "version": "3.0.0",
                "language": "ja_JP",
                "theme": "light"
            },
            "window": {
                "width": 1400,
                "height": 900,
                "maximized": False,
                "remember_size": True,
                "remember_position": True
            },
            "database": {
                "type": "sqlite",
                "path": "business_system.db",
                "backup_enabled": True,
                "backup_interval": 24,
                "auto_optimize": True
            },
            "ui": {
                "animation_enabled": True,
                "animation_duration": 300,
                "show_tooltips": True,
                "confirm_deletions": True,
                "auto_save": True,
                "auto_save_interval": 5
            },
            "features": {
                "plugins_enabled": True,
                "advanced_search": True,
                "dashboard_enabled": True,
                "notifications_enabled": True
            },
            "export": {
                "default_format": "xlsx",
                "include_headers": True,
                "date_format": "%Y-%m-%d",
                "currency_format": "¥{:,.0f}"
            }
        }
    
    def _get_default_themes(self) -> Dict[str, Any]:
        """デフォルトテーマを取得"""
        return {
            "light": {
                "name": "ライトテーマ",
                "colors": {
                    "primary": "#2196F3",
                    "secondary": "#FF9800",
                    "success": "#4CAF50",
                    "warning": "#FF5722",
                    "error": "#F44336",
                    "background": "#FAFAFA",
                    "surface": "#FFFFFF",
                    "text_primary": "#212121",
                    "text_secondary": "#757575",
                    "border": "#E0E0E0"
                },
                "fonts": {
                    "family": "Yu Gothic UI",
                    "size_small": 10,
                    "size_medium": 12,
                    "size_large": 14,
                    "size_title": 18
                }
            },
            "dark": {
                "name": "ダークテーマ",
                "colors": {
                    "primary": "#64B5F6",
                    "secondary": "#FFB74D",
                    "success": "#81C784",
                    "warning": "#E57373",
                    "error": "#EF5350",
                    "background": "#121212",
                    "surface": "#1E1E1E",
                    "text_primary": "#FFFFFF",
                    "text_secondary": "#B0B0B0",
                    "border": "#333333"
                },
                "fonts": {
                    "family": "Yu Gothic UI",
                    "size_small": 10,
                    "size_medium": 12,
                    "size_large": 14,
                    "size_title": 18
                }
            }
        }
    
    def get_stylesheet(self, theme_name: Optional[str] = None) -> str:
        """テーマに基づいたCSSスタイルシートを生成（PyQt6互換）"""
        theme = self.get_theme(theme_name)
        colors = theme.get("colors", {})
        fonts = theme.get("fonts", {})
        
        # プライマリカラーのバリエーション生成
        primary = colors.get('primary', '#2196F3')
        primary_hover = '#1976D2' if primary == '#2196F3' else primary
        primary_pressed = '#0D47A1' if primary == '#2196F3' else primary
        
        return f"""
        /* メインウィンドウ */
        QMainWindow {{
            background-color: {colors.get('background', '#FAFAFA')};
            color: {colors.get('text_primary', '#212121')};
            font-family: "{fonts.get('family', 'Yu Gothic UI')}";
            font-size: {fonts.get('size_medium', 12)}px;
        }}
        
        /* プライマリボタン */
        QPushButton.primary {{
            background-color: {primary};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }}
        
        QPushButton.primary:hover {{
            background-color: {primary_hover};
        }}
        
        QPushButton.primary:pressed {{
            background-color: {primary_pressed};
        }}
        
        /* セカンダリボタン */
        QPushButton.secondary {{
            background-color: {colors.get('secondary', '#FF9800')};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }}
        
        QPushButton.secondary:hover {{
            background-color: #F57C00;
        }}
        
        /* カード */
        QFrame.card {{
            background-color: {colors.get('surface', '#FFFFFF')};
            border: 1px solid {colors.get('border', '#E0E0E0')};
            border-radius: 8px;
            padding: 16px;
        }}
        
        /* テーブル */
        QTableView {{
            background-color: {colors.get('surface', '#FFFFFF')};
            alternate-background-color: {colors.get('background', '#FAFAFA')};
            gridline-color: {colors.get('border', '#E0E0E0')};
            selection-background-color: {primary};
        }}
        
        QHeaderView::section {{
            background-color: {primary};
            color: white;
            padding: 8px;
            border: none;
            font-weight: bold;
        }}
        
        /* 入力フィールド */
        QLineEdit, QTextEdit, QComboBox {{
            background-color: {colors.get('surface', '#FFFFFF')};
            border: 1px solid {colors.get('border', '#E0E0E0')};
            border-radius: 4px;
            padding: 8px;
            color: {colors.get('text_primary', '#212121')};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border-color: {primary};
        }}
        
        /* ツールバー */
        QToolBar {{
            background-color: {colors.get('surface', '#FFFFFF')};
            border: none;
            spacing: 8px;
            padding: 8px;
        }}
        
        /* ステータスバー */
        QStatusBar {{
            background-color: {colors.get('surface', '#FFFFFF')};
            border-top: 1px solid {colors.get('border', '#E0E0E0')};
            color: {colors.get('text_secondary', '#757575')};
        }}
        """
    
    def export_settings(self, file_path: str):
        """設定をファイルにエクスポート"""
        try:
            export_data = {
                "settings": self._settings,
                "themes": self._themes,
                "current_theme": self._current_theme
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"設定エクスポートエラー: {e}")
    
    def import_settings(self, file_path: str):
        """設定をファイルからインポート"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if "settings" in import_data:
                self._settings = import_data["settings"]
                self.save_settings()
            
            if "themes" in import_data:
                self._themes = import_data["themes"]
                self.save_themes()
            
            if "current_theme" in import_data:
                self.set_theme(import_data["current_theme"])
                
        except Exception as e:
            print(f"設定インポートエラー: {e}")


# グローバル設定マネージャインスタンス
config_manager = ConfigManager()