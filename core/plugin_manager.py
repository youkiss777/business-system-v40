#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v3.0 - プラグインマネージャー
拡張可能なプラグインシステムの実装
"""

import sys
import os
import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type
from pathlib import Path
import json
import logging
from dataclasses import dataclass, asdict
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """プラグイン情報"""
    name: str
    version: str
    description: str
    author: str
    module_name: str
    main_class: str
    dependencies: List[str]
    enabled: bool = True
    category: str = "general"
    icon: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginInfo':
        return cls(**data)


class PluginInterface(ABC):
    """プラグインインターフェース"""
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """プラグイン情報を取得"""
        pass
    
    @abstractmethod
    def initialize(self, app_context: QObject) -> bool:
        """プラグイン初期化"""
        pass
    
    @abstractmethod
    def get_widget(self) -> Optional[QWidget]:
        """メインウィジェットを取得"""
        pass
    
    @abstractmethod
    def get_menu_actions(self) -> List[QAction]:
        """メニューアクションを取得"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """プラグインクリーンアップ"""
        pass
    
    def get_settings_widget(self) -> Optional[QWidget]:
        """設定ウィジェットを取得（オプション）"""
        return None
    
    def on_theme_changed(self, theme: Dict[str, Any]) -> None:
        """テーマ変更通知（オプション）"""
        pass


class PluginManager(QObject):
    """プラグインマネージャー"""
    
    # シグナル
    plugin_loaded = pyqtSignal(str)  # プラグイン名
    plugin_unloaded = pyqtSignal(str)
    plugin_error = pyqtSignal(str, str)  # プラグイン名, エラーメッセージ
    
    def __init__(self, app_context: QObject):
        super().__init__()
        self.app_context = app_context
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_infos: Dict[str, PluginInfo] = {}
        self.plugin_paths: List[Path] = []
        self.config_file = Path("config/plugins.json")
        
        # デフォルトプラグインディレクトリ
        self.add_plugin_path(Path("plugins"))
        self.add_plugin_path(Path("modules/plugins"))
        
        # 設定読み込み
        self.load_config()
    
    def add_plugin_path(self, path: Path) -> None:
        """プラグインパスを追加"""
        if path.exists() and path not in self.plugin_paths:
            self.plugin_paths.append(path)
            
            # Pythonパスに追加
            str_path = str(path.absolute())
            if str_path not in sys.path:
                sys.path.insert(0, str_path)
    
    def scan_plugins(self) -> List[PluginInfo]:
        """プラグインをスキャン"""
        found_plugins = []
        
        for plugin_path in self.plugin_paths:
            if not plugin_path.exists():
                continue
            
            # plugin.json ファイルを探す
            for plugin_dir in plugin_path.iterdir():
                if not plugin_dir.is_dir():
                    continue
                
                plugin_json = plugin_dir / "plugin.json"
                if plugin_json.exists():
                    try:
                        with open(plugin_json, 'r', encoding='utf-8') as f:
                            plugin_data = json.load(f)
                        
                        plugin_info = PluginInfo.from_dict(plugin_data)
                        found_plugins.append(plugin_info)
                        
                    except Exception as e:
                        logger.error(f"プラグイン情報読み込みエラー {plugin_dir}: {e}")
        
        return found_plugins
    
    def load_plugin(self, plugin_info: PluginInfo) -> bool:
        """プラグインを読み込み"""
        try:
            # 依存関係チェック
            if not self._check_dependencies(plugin_info.dependencies):
                raise ImportError(f"依存関係が満たされていません: {plugin_info.dependencies}")
            
            # モジュール読み込み
            module = importlib.import_module(plugin_info.module_name)
            
            # メインクラス取得
            plugin_class = getattr(module, plugin_info.main_class)
            
            # インターフェースチェック
            if not issubclass(plugin_class, PluginInterface):
                raise TypeError("プラグインはPluginInterfaceを継承する必要があります")
            
            # インスタンス作成
            plugin_instance = plugin_class()
            
            # 初期化
            if plugin_instance.initialize(self.app_context):
                self.plugins[plugin_info.name] = plugin_instance
                self.plugin_infos[plugin_info.name] = plugin_info
                
                logger.info(f"プラグイン読み込み成功: {plugin_info.name}")
                self.plugin_loaded.emit(plugin_info.name)
                return True
            else:
                raise RuntimeError("プラグイン初期化に失敗しました")
                
        except Exception as e:
            error_msg = f"プラグイン読み込みエラー {plugin_info.name}: {e}"
            logger.error(error_msg)
            self.plugin_error.emit(plugin_info.name, str(e))
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """プラグインをアンロード"""
        try:
            if plugin_name in self.plugins:
                plugin = self.plugins[plugin_name]
                plugin.cleanup()
                
                del self.plugins[plugin_name]
                del self.plugin_infos[plugin_name]
                
                logger.info(f"プラグインアンロード成功: {plugin_name}")
                self.plugin_unloaded.emit(plugin_name)
                return True
            return False
            
        except Exception as e:
            error_msg = f"プラグインアンロードエラー {plugin_name}: {e}"
            logger.error(error_msg)
            self.plugin_error.emit(plugin_name, str(e))
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """プラグインインスタンスを取得"""
        return self.plugins.get(plugin_name)
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """プラグイン情報を取得"""
        return self.plugin_infos.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, PluginInterface]:
        """すべてのプラグインを取得"""
        return self.plugins.copy()
    
    def get_plugins_by_category(self, category: str) -> Dict[str, PluginInterface]:
        """カテゴリ別プラグインを取得"""
        result = {}
        for name, plugin in self.plugins.items():
            plugin_info = self.plugin_infos.get(name)
            if plugin_info and plugin_info.category == category:
                result[name] = plugin
        return result
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """プラグインを再読み込み"""
        if plugin_name in self.plugins:
            plugin_info = self.plugin_infos[plugin_name]
            if self.unload_plugin(plugin_name):
                return self.load_plugin(plugin_info)
        return False
    
    def load_all_enabled_plugins(self) -> None:
        """有効なプラグインをすべて読み込み"""
        available_plugins = self.scan_plugins()
        
        for plugin_info in available_plugins:
            if plugin_info.enabled:
                self.load_plugin(plugin_info)
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """プラグインを有効化"""
        if plugin_name in self.plugin_infos:
            self.plugin_infos[plugin_name].enabled = True
            self.save_config()
            return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """プラグインを無効化"""
        if plugin_name in self.plugin_infos:
            self.plugin_infos[plugin_name].enabled = False
            self.unload_plugin(plugin_name)
            self.save_config()
            return True
        return False
    
    def install_plugin(self, plugin_path: Path) -> bool:
        """プラグインをインストール"""
        try:
            # ZIPファイルの解凍やファイルコピー処理
            # 実装は将来の拡張として保留
            pass
        except Exception as e:
            logger.error(f"プラグインインストールエラー: {e}")
            return False
    
    def uninstall_plugin(self, plugin_name: str) -> bool:
        """プラグインをアンインストール"""
        try:
            # プラグインファイルの削除処理
            # 実装は将来の拡張として保留
            pass
        except Exception as e:
            logger.error(f"プラグインアンインストールエラー: {e}")
            return False
    
    def notify_theme_changed(self, theme: Dict[str, Any]) -> None:
        """テーマ変更をプラグインに通知"""
        for plugin in self.plugins.values():
            try:
                plugin.on_theme_changed(theme)
            except Exception as e:
                logger.error(f"プラグインテーマ変更通知エラー: {e}")
    
    def _check_dependencies(self, dependencies: List[str]) -> bool:
        """依存関係チェック"""
        for dep in dependencies:
            try:
                importlib.import_module(dep)
            except ImportError:
                return False
        return True
    
    def load_config(self) -> None:
        """設定を読み込み"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # プラグイン有効/無効状態を復元
                plugin_states = config.get('plugin_states', {})
                for plugin_name, enabled in plugin_states.items():
                    if plugin_name in self.plugin_infos:
                        self.plugin_infos[plugin_name].enabled = enabled
                        
        except Exception as e:
            logger.error(f"プラグイン設定読み込みエラー: {e}")
    
    def save_config(self) -> None:
        """設定を保存"""
        try:
            # ディレクトリ作成
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 設定データ作成
            plugin_states = {}
            for name, info in self.plugin_infos.items():
                plugin_states[name] = info.enabled
            
            config = {
                'plugin_states': plugin_states,
                'plugin_paths': [str(p) for p in self.plugin_paths]
            }
            
            # ファイル保存
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"プラグイン設定保存エラー: {e}")


class PluginRegistry:
    """プラグイン登録レジストリ"""
    
    _plugins: Dict[str, Type[PluginInterface]] = {}
    
    @classmethod
    def register(cls, plugin_class: Type[PluginInterface]) -> None:
        """プラグインクラスを登録"""
        if not issubclass(plugin_class, PluginInterface):
            raise TypeError("プラグインはPluginInterfaceを継承する必要があります")
        
        # プラグイン情報を取得してキーとして使用
        temp_instance = plugin_class()
        plugin_info = temp_instance.get_info()
        cls._plugins[plugin_info.name] = plugin_class
    
    @classmethod
    def get_plugin_class(cls, plugin_name: str) -> Optional[Type[PluginInterface]]:
        """プラグインクラスを取得"""
        return cls._plugins.get(plugin_name)
    
    @classmethod
    def get_all_plugin_classes(cls) -> Dict[str, Type[PluginInterface]]:
        """すべてのプラグインクラスを取得"""
        return cls._plugins.copy()


def plugin_decorator(info: PluginInfo):
    """プラグインデコレータ"""
    def decorator(plugin_class: Type[PluginInterface]):
        # プラグイン情報を埋め込み
        plugin_class._plugin_info = info
        
        # レジストリに登録
        PluginRegistry.register(plugin_class)
        
        return plugin_class
    return decorator