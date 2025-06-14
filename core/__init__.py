"""
業務支援システム v3.0 - コアモジュール
PyQt6 ベースのモダンな業務管理システム
"""

__version__ = "3.0.0"
__author__ = "Business System Development Team"

from .app import BusinessApp
from .config_manager import ConfigManager
from .database import DatabaseManager

__all__ = ['BusinessApp', 'ConfigManager', 'DatabaseManager']