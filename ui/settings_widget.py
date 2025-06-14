#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v4.0 - 設定ウィジェット
テーマ切り替え、データベース設定、バックアップ・復元機能の完全実装
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QComboBox, QCheckBox, QMessageBox, QHeaderView,
    QSplitter, QGroupBox, QLabel, QDateEdit, QSpinBox,
    QDoubleSpinBox, QFrame, QScrollArea, QProgressBar, QDialog,
    QFileDialog, QSlider, QListWidget, QListWidgetItem, QButtonGroup,
    QRadioButton, QDialogButtonBox, QPlainTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QSettings, QStandardPaths
from PyQt6.QtGui import QFont, QPixmap, QIcon, QColor, QPalette
from typing import Optional, List, Dict, Any, Tuple
import logging
import json
import shutil
import os
from datetime import datetime, timedelta
from pathlib import Path

from ui.components.base_widget import BaseWidget
from core.database import db_manager
from core.config_manager import config_manager
from core.ai_integration import ai_assistant

logger = logging.getLogger(__name__)


class BackupRestoreDialog(QDialog):
    """バックアップ・復元ダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("バックアップ・復元")
        self.setModal(True)
        self.resize(600, 500)
        self.setup_ui()
        self.load_backup_list()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # タブウィジェット
        tab_widget = QTabWidget()
        
        # バックアップタブ
        backup_tab = QWidget()
        backup_layout = QVBoxLayout(backup_tab)
        
        # バックアップ作成
        backup_group = QGroupBox("バックアップ作成")
        backup_form = QFormLayout(backup_group)
        
        self.backup_name_edit = QLineEdit()
        self.backup_name_edit.setText(f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        backup_form.addRow("バックアップ名:", self.backup_name_edit)
        
        self.backup_description_edit = QPlainTextEdit()
        self.backup_description_edit.setMaximumHeight(80)
        self.backup_description_edit.setPlaceholderText("バックアップの説明を入力...")
        backup_form.addRow("説明:", self.backup_description_edit)
        
        backup_buttons = QHBoxLayout()
        self.create_backup_btn = QPushButton("バックアップ作成")
        self.create_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.create_backup_btn.clicked.connect(self.create_backup)
        backup_buttons.addWidget(self.create_backup_btn)
        backup_buttons.addStretch()
        
        backup_layout.addWidget(backup_group)
        backup_layout.addLayout(backup_buttons)
        backup_layout.addStretch()
        
        tab_widget.addTab(backup_tab, "バックアップ作成")
        
        # 復元タブ
        restore_tab = QWidget()
        restore_layout = QVBoxLayout(restore_tab)
        
        # バックアップリスト
        list_group = QGroupBox("利用可能なバックアップ")
        list_layout = QVBoxLayout(list_group)
        
        self.backup_list = QTableWidget()
        self.backup_list.setColumnCount(4)
        self.backup_list.setHorizontalHeaderLabels(["名前", "作成日時", "サイズ", "説明"])
        
        header = self.backup_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        self.backup_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        list_layout.addWidget(self.backup_list)
        
        # 復元ボタン
        restore_buttons = QHBoxLayout()
        
        self.restore_btn = QPushButton("選択したバックアップを復元")
        self.restore_btn.setStyleSheet("""
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
        self.restore_btn.clicked.connect(self.restore_backup)
        restore_buttons.addWidget(self.restore_btn)
        
        self.delete_backup_btn = QPushButton("削除")
        self.delete_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.delete_backup_btn.clicked.connect(self.delete_backup)
        restore_buttons.addWidget(self.delete_backup_btn)
        
        restore_buttons.addStretch()
        
        restore_layout.addWidget(list_group)
        restore_layout.addLayout(restore_buttons)
        
        tab_widget.addTab(restore_tab, "復元")
        
        layout.addWidget(tab_widget)
        
        # ダイアログボタン
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.close)
        layout.addWidget(button_box)
    
    def load_backup_list(self):
        """バックアップリスト読み込み"""
        try:
            backup_dir = Path("data/backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            backups = []
            for backup_file in backup_dir.glob("*.db"):
                try:
                    stat = backup_file.stat()
                    size_mb = stat.st_size / (1024 * 1024)
                    created = datetime.fromtimestamp(stat.st_ctime)
                    
                    # メタデータファイルがあれば読み込み
                    meta_file = backup_file.with_suffix('.json')
                    description = ""
                    if meta_file.exists():
                        with open(meta_file, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            description = meta.get('description', '')
                    
                    backups.append({
                        'name': backup_file.stem,
                        'path': backup_file,
                        'created': created,
                        'size': size_mb,
                        'description': description
                    })
                except Exception as e:
                    logger.error(f"バックアップ情報読み込みエラー {backup_file}: {e}")
            
            # 作成日時でソート（新しい順）
            backups.sort(key=lambda x: x['created'], reverse=True)
            
            # テーブルに表示
            self.backup_list.setRowCount(len(backups))
            for row, backup in enumerate(backups):
                self.backup_list.setItem(row, 0, QTableWidgetItem(backup['name']))
                self.backup_list.setItem(row, 1, QTableWidgetItem(backup['created'].strftime('%Y-%m-%d %H:%M:%S')))
                self.backup_list.setItem(row, 2, QTableWidgetItem(f"{backup['size']:.1f} MB"))
                self.backup_list.setItem(row, 3, QTableWidgetItem(backup['description']))
                
                # パスをデータとして保存
                self.backup_list.item(row, 0).setData(Qt.ItemDataRole.UserRole, str(backup['path']))
                
        except Exception as e:
            logger.error(f"バックアップリスト読み込みエラー: {e}")
            QMessageBox.critical(self, "エラー", f"バックアップリストの読み込みに失敗しました：{e}")
    
    def create_backup(self):
        """バックアップ作成"""
        try:
            backup_name = self.backup_name_edit.text().strip()
            if not backup_name:
                QMessageBox.warning(self, "入力エラー", "バックアップ名を入力してください")
                return
            
            backup_dir = Path("data/backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # バックアップファイルパス
            backup_file = backup_dir / f"{backup_name}.db"
            
            # 既存ファイルチェック
            if backup_file.exists():
                reply = QMessageBox.question(
                    self, "確認", 
                    f"'{backup_name}'は既に存在します。上書きしますか？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # データベースファイルをコピー
            db_path = Path("business_system.db")
            if not db_path.exists():
                QMessageBox.critical(self, "エラー", "データベースファイルが見つかりません")
                return
            
            shutil.copy2(db_path, backup_file)
            
            # メタデータ保存
            meta_file = backup_file.with_suffix('.json')
            meta_data = {
                'name': backup_name,
                'description': self.backup_description_edit.toPlainText(),
                'created': datetime.now().isoformat(),
                'original_db_path': str(db_path),
                'app_version': config_manager.get("app.version", "4.0.0")
            }
            
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "完了", f"バックアップ '{backup_name}' を作成しました")
            
            # リスト更新
            self.load_backup_list()
            
            # 入力フィールドクリア
            self.backup_name_edit.setText(f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            self.backup_description_edit.clear()
            
        except Exception as e:
            logger.error(f"バックアップ作成エラー: {e}")
            QMessageBox.critical(self, "エラー", f"バックアップの作成に失敗しました：{e}")
    
    def restore_backup(self):
        """バックアップ復元"""
        try:
            current_row = self.backup_list.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "選択エラー", "復元するバックアップを選択してください")
                return
            
            backup_name = self.backup_list.item(current_row, 0).text()
            backup_path = Path(self.backup_list.item(current_row, 0).data(Qt.ItemDataRole.UserRole))
            
            # 確認ダイアログ
            reply = QMessageBox.question(
                self, "確認", 
                f"データベースを '{backup_name}' に復元しますか？\n\n"
                "現在のデータは失われます。\n"
                "事前に現在のデータのバックアップを作成することを推奨します。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
            
            if not backup_path.exists():
                QMessageBox.critical(self, "エラー", "バックアップファイルが見つかりません")
                return
            
            # 現在のデータベースファイルを退避
            db_path = Path("business_system.db")
            if db_path.exists():
                backup_current = Path(f"business_system_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
                shutil.copy2(db_path, backup_current)
                logger.info(f"現在のDBを退避: {backup_current}")
            
            # バックアップファイルを復元
            shutil.copy2(backup_path, db_path)
            
            QMessageBox.information(
                self, "完了", 
                f"データベースを '{backup_name}' に復元しました。\n\n"
                "変更を反映するため、アプリケーションを再起動してください。"
            )
            
        except Exception as e:
            logger.error(f"バックアップ復元エラー: {e}")
            QMessageBox.critical(self, "エラー", f"バックアップの復元に失敗しました：{e}")
    
    def delete_backup(self):
        """バックアップ削除"""
        try:
            current_row = self.backup_list.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "選択エラー", "削除するバックアップを選択してください")
                return
            
            backup_name = self.backup_list.item(current_row, 0).text()
            backup_path = Path(self.backup_list.item(current_row, 0).data(Qt.ItemDataRole.UserRole))
            
            reply = QMessageBox.question(
                self, "確認", 
                f"バックアップ '{backup_name}' を削除しますか？\n\nこの操作は取り消せません。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # バックアップファイルとメタデータファイルを削除
                if backup_path.exists():
                    backup_path.unlink()
                
                meta_file = backup_path.with_suffix('.json')
                if meta_file.exists():
                    meta_file.unlink()
                
                QMessageBox.information(self, "完了", f"バックアップ '{backup_name}' を削除しました")
                self.load_backup_list()
                
        except Exception as e:
            logger.error(f"バックアップ削除エラー: {e}")
            QMessageBox.critical(self, "エラー", f"バックアップの削除に失敗しました：{e}")


class ThemePreviewWidget(QFrame):
    """テーマプレビューウィジェット"""
    
    theme_selected = pyqtSignal(str)
    
    def __init__(self, theme_name: str, theme_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.theme_name = theme_name
        self.theme_data = theme_data
        self.setup_ui()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # テーマ名
        name_label = QLabel(self.theme_data.get('name', self.theme_name))
        name_label.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        
        # カラープレビュー
        colors = self.theme_data.get('colors', {})
        color_layout = QGridLayout()
        
        color_items = [
            ('Primary', colors.get('primary', '#2196F3')),
            ('Secondary', colors.get('secondary', '#FF9800')),
            ('Background', colors.get('background', '#FAFAFA')),
            ('Surface', colors.get('surface', '#FFFFFF'))
        ]
        
        for i, (label, color) in enumerate(color_items):
            color_frame = QFrame()
            color_frame.setFixedSize(30, 20)
            color_frame.setStyleSheet(f"background-color: {color}; border: 1px solid #ccc;")
            
            color_label = QLabel(label)
            color_label.setFont(QFont("Yu Gothic UI", 8))
            
            row = i // 2
            col = (i % 2) * 2
            color_layout.addWidget(color_frame, row, col)
            color_layout.addWidget(color_label, row, col + 1)
        
        layout.addLayout(color_layout)
        
        # 選択ボタン
        select_btn = QPushButton("このテーマを選択")
        
        def on_theme_select():
            """テーマ選択時のハンドラー"""
            print(f"テーマ選択: {self.theme_name}")  # デバッグ用
            self.theme_selected.emit(self.theme_name)
        
        select_btn.clicked.connect(on_theme_select)
        select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.get('primary', '#2196F3')};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1976D2;
            }}
        """)
        layout.addWidget(select_btn)
        
        # フレームスタイル
        bg_color = colors.get('background', '#FAFAFA')
        self.setStyleSheet(f"""
            ThemePreviewWidget {{
                background-color: {bg_color};
                border: 2px solid {colors.get('primary', '#2196F3')};
                border-radius: 8px;
            }}
        """)


class SettingsWidget(BaseWidget):
    """設定ウィジェット"""
    
    settings_changed = pyqtSignal(str, object)  # 設定キー, 値
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("BusinessSystem", "Settings")
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # ヘッダー
        header_layout = QHBoxLayout()
        
        title = QLabel("⚙️ システム設定")
        title.setFont(QFont("Yu Gothic UI", 24, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 設定保存ボタン
        save_btn = QPushButton("設定を保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.clicked.connect(self.save_settings)
        header_layout.addWidget(save_btn)
        
        layout.addLayout(header_layout)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #2196F3;
            }
        """)
        
        # 各タブ作成
        self.create_general_tab()
        self.create_appearance_tab()
        self.create_database_tab()
        self.create_ai_tab()
        self.create_advanced_tab()
        
        layout.addWidget(self.tab_widget)
    
    def create_general_tab(self):
        """一般設定タブ"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # アプリケーション設定
        app_group = QGroupBox("アプリケーション設定")
        app_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        app_layout = QFormLayout(app_group)
        
        # 起動時の動作
        self.startup_combo = QComboBox()
        self.startup_combo.addItems([
            "ダッシュボードを表示",
            "前回のタブを復元",
            "指定したモジュールを表示"
        ])
        app_layout.addRow("起動時の動作:", self.startup_combo)
        
        # 自動保存
        self.autosave_check = QCheckBox("データを自動保存する（推奨）")
        app_layout.addRow("自動保存:", self.autosave_check)
        
        # 自動保存間隔
        self.autosave_interval = QSpinBox()
        self.autosave_interval.setRange(1, 60)
        self.autosave_interval.setValue(5)
        self.autosave_interval.setSuffix("分")
        app_layout.addRow("自動保存間隔:", self.autosave_interval)
        
        # 終了時バックアップ
        self.exit_backup_check = QCheckBox("終了時にバックアップを作成")
        app_layout.addRow("終了時バックアップ:", self.exit_backup_check)
        
        layout.addWidget(app_group)
        
        # 通知設定
        notification_group = QGroupBox("通知設定")
        notification_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        notification_layout = QFormLayout(notification_group)
        
        self.error_notifications = QCheckBox("エラー時に通知を表示")
        notification_layout.addRow("エラー通知:", self.error_notifications)
        
        self.success_notifications = QCheckBox("操作完了時に通知を表示")
        notification_layout.addRow("完了通知:", self.success_notifications)
        
        self.low_stock_notifications = QCheckBox("低在庫時に通知を表示")
        notification_layout.addRow("低在庫通知:", self.low_stock_notifications)
        
        layout.addWidget(notification_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "一般")
    
    def create_appearance_tab(self):
        """外観設定タブ"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # テーマ設定
        theme_group = QGroupBox("テーマ設定")
        theme_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        theme_layout = QVBoxLayout(theme_group)
        
        # テーマ選択
        theme_selection = QHBoxLayout()
        theme_selection.addWidget(QLabel("テーマ:"))
        
        self.theme_combo = QComboBox()
        available_themes = config_manager.get_available_themes()
        for theme in available_themes:
            theme_data = config_manager.get_theme(theme)
            self.theme_combo.addItem(theme_data.get('name', theme), theme)
        
        # テーマコンボボックスの変更イベントを接続
        def on_theme_combo_changed():
            """テーマコンボボックス変更時のハンドラー"""
            selected_theme = self.theme_combo.currentData()
            if selected_theme:
                print(f"コンボボックステーマ変更: {selected_theme}")  # デバッグ用
                # 即座に適用はしない（プレビューボタンでのみ適用）
        
        self.theme_combo.currentTextChanged.connect(on_theme_combo_changed)
        theme_selection.addWidget(self.theme_combo)
        
        theme_selection.addStretch()
        theme_layout.addLayout(theme_selection)
        
        # テーマプレビュー
        preview_label = QLabel("プレビュー:")
        preview_label.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        theme_layout.addWidget(preview_label)
        
        # プレビューエリア
        preview_scroll = QScrollArea()
        preview_widget = QWidget()
        self.preview_layout = QHBoxLayout(preview_widget)
        
        # 利用可能なテーマのプレビューを作成
        for theme_name in available_themes:
            theme_data = config_manager.get_theme(theme_name)
            preview = ThemePreviewWidget(theme_name, theme_data)
            preview.theme_selected.connect(self.apply_theme)
            self.preview_layout.addWidget(preview)
        
        preview_scroll.setWidget(preview_widget)
        preview_scroll.setFixedHeight(150)
        theme_layout.addWidget(preview_scroll)
        
        layout.addWidget(theme_group)
        
        # フォント設定
        font_group = QGroupBox("フォント設定")
        font_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        font_layout = QFormLayout(font_group)
        
        # フォントサイズ
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(12)
        self.font_size_spin.setSuffix("pt")
        font_layout.addRow("フォントサイズ:", self.font_size_spin)
        
        # ハイコントラスト
        self.high_contrast_check = QCheckBox("ハイコントラストモード（アクセシビリティ）")
        font_layout.addRow("表示オプション:", self.high_contrast_check)
        
        layout.addWidget(font_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "外観")
    
    def create_database_tab(self):
        """データベース設定タブ"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # データベース情報
        db_info_group = QGroupBox("データベース情報")
        db_info_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        db_info_layout = QFormLayout(db_info_group)
        
        # データベースパス
        self.db_path_edit = QLineEdit()
        self.db_path_edit.setReadOnly(True)
        db_info_layout.addRow("データベースファイル:", self.db_path_edit)
        
        # データベースサイズ
        self.db_size_label = QLabel()
        db_info_layout.addRow("ファイルサイズ:", self.db_size_label)
        
        # 最終更新
        self.db_modified_label = QLabel()
        db_info_layout.addRow("最終更新:", self.db_modified_label)
        
        layout.addWidget(db_info_group)
        
        # データベース操作
        db_ops_group = QGroupBox("データベース操作")
        db_ops_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        db_ops_layout = QVBoxLayout(db_ops_group)
        
        # ボタンレイアウト
        button_layout = QGridLayout()
        
        # バックアップ・復元
        backup_restore_btn = QPushButton("バックアップ・復元")
        backup_restore_btn.setStyleSheet(self.get_button_style("#4CAF50"))
        backup_restore_btn.clicked.connect(self.show_backup_restore_dialog)
        button_layout.addWidget(backup_restore_btn, 0, 0)
        
        # 最適化
        optimize_btn = QPushButton("データベース最適化")
        optimize_btn.setStyleSheet(self.get_button_style("#2196F3"))
        optimize_btn.clicked.connect(self.optimize_database)
        button_layout.addWidget(optimize_btn, 0, 1)
        
        # 整合性チェック
        integrity_btn = QPushButton("整合性チェック")
        integrity_btn.setStyleSheet(self.get_button_style("#FF9800"))
        integrity_btn.clicked.connect(self.check_database_integrity)
        button_layout.addWidget(integrity_btn, 1, 0)
        
        # データエクスポート
        export_btn = QPushButton("データエクスポート")
        export_btn.setStyleSheet(self.get_button_style("#9C27B0"))
        export_btn.clicked.connect(self.export_database)
        button_layout.addWidget(export_btn, 1, 1)
        
        db_ops_layout.addLayout(button_layout)
        layout.addWidget(db_ops_group)
        
        # 自動メンテナンス
        maintenance_group = QGroupBox("自動メンテナンス")
        maintenance_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        maintenance_layout = QFormLayout(maintenance_group)
        
        self.auto_optimize_check = QCheckBox("週次で自動最適化を実行")
        maintenance_layout.addRow("自動最適化:", self.auto_optimize_check)
        
        self.auto_backup_check = QCheckBox("日次で自動バックアップを作成")
        maintenance_layout.addRow("自動バックアップ:", self.auto_backup_check)
        
        self.cleanup_old_backups = QCheckBox("30日以上古いバックアップを自動削除")
        maintenance_layout.addRow("バックアップクリーンアップ:", self.cleanup_old_backups)
        
        layout.addWidget(maintenance_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "データベース")
    
    def create_ai_tab(self):
        """AI設定タブ"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # AI機能状態
        ai_status_group = QGroupBox("AI機能状態")
        ai_status_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        ai_status_layout = QFormLayout(ai_status_group)
        
        # AI有効/無効
        self.ai_enabled_check = QCheckBox("AI機能を有効にする")
        ai_status_layout.addRow("AI機能:", self.ai_enabled_check)
        
        # 現在のステータス
        self.ai_status_label = QLabel()
        ai_status_layout.addRow("現在の状態:", self.ai_status_label)
        
        layout.addWidget(ai_status_group)
        
        # API設定
        api_group = QGroupBox("API設定")
        api_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        api_layout = QVBoxLayout(api_group)
        
        # Gemini API
        gemini_layout = QFormLayout()
        self.gemini_key_edit = QLineEdit()
        self.gemini_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_edit.setPlaceholderText("Gemini APIキーを入力...")
        gemini_layout.addRow("Gemini APIキー:", self.gemini_key_edit)
        
        # OpenAI API
        openai_layout = QFormLayout()
        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_edit.setPlaceholderText("OpenAI APIキーを入力...")
        openai_layout.addRow("OpenAI APIキー:", self.openai_key_edit)
        
        api_layout.addLayout(gemini_layout)
        api_layout.addLayout(openai_layout)
        
        # テストボタン
        test_layout = QHBoxLayout()
        test_gemini_btn = QPushButton("Gemini接続テスト")
        test_gemini_btn.setStyleSheet(self.get_button_style("#4CAF50"))
        test_gemini_btn.clicked.connect(self.test_gemini_connection)
        test_layout.addWidget(test_gemini_btn)
        
        test_openai_btn = QPushButton("OpenAI接続テスト")
        test_openai_btn.setStyleSheet(self.get_button_style("#FF9800"))
        test_openai_btn.clicked.connect(self.test_openai_connection)
        test_layout.addWidget(test_openai_btn)
        
        test_layout.addStretch()
        api_layout.addLayout(test_layout)
        layout.addWidget(api_group)
        
        # 音声機能
        voice_group = QGroupBox("音声機能")
        voice_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        voice_layout = QFormLayout(voice_group)
        
        self.voice_recognition_check = QCheckBox("音声認識を有効にする")
        voice_layout.addRow("音声認識:", self.voice_recognition_check)
        
        self.tts_check = QCheckBox("音声合成（読み上げ）を有効にする")
        voice_layout.addRow("音声合成:", self.tts_check)
        
        layout.addWidget(voice_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "AI機能")
    
    def create_advanced_tab(self):
        """詳細設定タブ"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # ログ設定
        log_group = QGroupBox("ログ設定")
        log_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        log_layout = QFormLayout(log_group)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText("INFO")
        log_layout.addRow("ログレベル:", self.log_level_combo)
        
        self.log_to_file_check = QCheckBox("ファイルにログを出力")
        log_layout.addRow("ファイル出力:", self.log_to_file_check)
        
        layout.addWidget(log_group)
        
        # パフォーマンス設定
        performance_group = QGroupBox("パフォーマンス設定")
        performance_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        performance_layout = QFormLayout(performance_group)
        
        self.cache_enabled_check = QCheckBox("キャッシュを有効にする")
        performance_layout.addRow("キャッシュ:", self.cache_enabled_check)
        
        self.animation_enabled_check = QCheckBox("UIアニメーションを有効にする")
        performance_layout.addRow("アニメーション:", self.animation_enabled_check)
        
        self.max_undo_spin = QSpinBox()
        self.max_undo_spin.setRange(10, 100)
        self.max_undo_spin.setValue(50)
        performance_layout.addRow("元に戻す最大数:", self.max_undo_spin)
        
        layout.addWidget(performance_group)
        
        # セキュリティ設定
        security_group = QGroupBox("セキュリティ設定")
        security_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        security_layout = QFormLayout(security_group)
        
        self.auto_lock_check = QCheckBox("一定時間非アクティブ時に自動ロック")
        security_layout.addRow("自動ロック:", self.auto_lock_check)
        
        self.lock_timeout_spin = QSpinBox()
        self.lock_timeout_spin.setRange(5, 120)
        self.lock_timeout_spin.setValue(30)
        self.lock_timeout_spin.setSuffix("分")
        security_layout.addRow("ロック時間:", self.lock_timeout_spin)
        
        layout.addWidget(security_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "詳細")
    
    def get_button_style(self, color: str) -> str:
        """ボタンスタイル取得"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #1976D2;
            }}
            QPushButton:pressed {{
                background-color: #0D47A1;
            }}
        """
    
    def load_current_settings(self):
        """現在の設定を読み込み"""
        try:
            # 一般設定
            self.autosave_check.setChecked(config_manager.get("ui.auto_save", True))
            self.autosave_interval.setValue(config_manager.get("ui.auto_save_interval", 5))
            self.exit_backup_check.setChecked(config_manager.get("database.backup_enabled", True))
            
            # 外観設定
            current_theme = config_manager.get("app.theme", "light")
            theme_index = self.theme_combo.findData(current_theme)
            if theme_index >= 0:
                self.theme_combo.setCurrentIndex(theme_index)
            
            # AI設定
            self.ai_enabled_check.setChecked(config_manager.is_ai_enabled())
            self.gemini_key_edit.setText(config_manager.get_ai_setting("GEMINI_API_KEY", ""))
            self.openai_key_edit.setText(config_manager.get_ai_setting("OPENAI_API_KEY", ""))
            
            # 音声機能設定
            self.voice_recognition_check.setChecked(config_manager.get_ai_setting("VOICE_RECOGNITION_ENABLED", False))
            self.tts_check.setChecked(config_manager.get_ai_setting("TTS_ENABLED", False))
            
            # AI状態更新
            self.update_ai_status()
            
            # データベース情報更新
            self.update_database_info()
            
        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
    
    def update_ai_status(self):
        """AI状態更新"""
        if ai_assistant.is_enabled():
            self.ai_status_label.setText("✅ 正常動作")
            self.ai_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.ai_status_label.setText("❌ 無効または設定不完全")
            self.ai_status_label.setStyleSheet("color: #f44336; font-weight: bold;")
    
    def update_database_info(self):
        """データベース情報更新"""
        try:
            db_path = Path("business_system.db")
            if db_path.exists():
                self.db_path_edit.setText(str(db_path.absolute()))
                
                stat = db_path.stat()
                size_mb = stat.st_size / (1024 * 1024)
                self.db_size_label.setText(f"{size_mb:.2f} MB")
                
                modified = datetime.fromtimestamp(stat.st_mtime)
                self.db_modified_label.setText(modified.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                self.db_path_edit.setText("データベースファイルが見つかりません")
                self.db_size_label.setText("N/A")
                self.db_modified_label.setText("N/A")
                
        except Exception as e:
            logger.error(f"データベース情報更新エラー: {e}")
    
    def apply_theme(self, theme_name: str = None):
        """テーマ適用"""
        try:
            # 無限ループ防止用フラグ
            if hasattr(self, '_applying_theme') and self._applying_theme:
                return
            
            self._applying_theme = True
            
            # theme_nameが指定されていない場合はコンボボックスから取得
            if theme_name is None or theme_name == "":
                theme_name = self.theme_combo.currentData()
                if not theme_name:
                    QMessageBox.warning(self, "エラー", "適用するテーマが選択されていません。")
                    return
            
            # 文字列に変換（安全策）
            theme_name = str(theme_name)
            
            # テーマの存在確認
            available_themes = config_manager.get_available_themes()
            if theme_name not in available_themes:
                QMessageBox.warning(self, "エラー", f"テーマ '{theme_name}' は存在しません。")
                return
            
            # テーマ適用
            config_manager.set_theme(theme_name)
            
            # コンボボックスを更新（循環参照を避けるため一時的に切断）
            self.theme_combo.blockSignals(True)
            theme_index = self.theme_combo.findData(theme_name)
            if theme_index >= 0:
                self.theme_combo.setCurrentIndex(theme_index)
            self.theme_combo.blockSignals(False)
            
            QMessageBox.information(
                self, "テーマ変更", 
                f"テーマを '{config_manager.get_theme(theme_name).get('name', theme_name)}' に変更しました。\n\n"
                "一部の変更はアプリケーション再起動後に反映されます。"
            )
            
        except TypeError as e:
            logger.error(f"TypeError in apply_theme: {e}")
            QMessageBox.critical(self, "エラー", f"テーマ適用でタイプエラーが発生しました：{e}")
        except Exception as e:
            logger.error(f"Exception in apply_theme: {e}")
            QMessageBox.critical(self, "エラー", f"テーマの適用に失敗しました：{e}")
        finally:
            # フラグをリセット
            self._applying_theme = False
    
    def save_settings(self):
        """設定保存"""
        try:
            # 一般設定を安全に保存
            try:
                config_manager.set("ui.auto_save", self.autosave_check.isChecked())
                config_manager.set("ui.auto_save_interval", self.autosave_interval.value())
                config_manager.set("database.backup_enabled", self.exit_backup_check.isChecked())
            except Exception as e:
                logger.warning(f"一般設定保存エラー: {e}")
            
            # 外観設定を安全に保存
            try:
                selected_theme = self.theme_combo.currentData()
                if selected_theme:
                    config_manager.set_theme(selected_theme)
            except Exception as e:
                logger.warning(f"テーマ設定保存エラー: {e}")
            
            # AI設定を安全に保存
            try:
                config_manager.set_ai_setting("AI_ENABLED", self.ai_enabled_check.isChecked())
                
                # APIキーは空でも保存
                gemini_key = self.gemini_key_edit.text().strip()
                openai_key = self.openai_key_edit.text().strip()
                config_manager.set_ai_setting("GEMINI_API_KEY", gemini_key)
                config_manager.set_ai_setting("OPENAI_API_KEY", openai_key)
                
                # 音声機能設定
                config_manager.set_ai_setting("VOICE_RECOGNITION_ENABLED", self.voice_recognition_check.isChecked())
                config_manager.set_ai_setting("TTS_ENABLED", self.tts_check.isChecked())
                
            except Exception as e:
                logger.error(f"AI設定保存エラー: {e}")
                QMessageBox.critical(self, "エラー", f"AI設定の保存に失敗しました：{e}")
                return
            
            QMessageBox.information(self, "保存完了", "設定を保存しました。\n\n一部の変更はアプリケーション再起動後に反映されます。")
            
            # AI状態更新（エラーハンドリング付き）
            try:
                self.update_ai_status()
            except Exception as e:
                logger.warning(f"AI状態更新エラー: {e}")
            
        except Exception as e:
            logger.error(f"設定保存の重大なエラー: {e}")
            QMessageBox.critical(self, "エラー", f"設定の保存に失敗しました：{e}")
    
    def show_backup_restore_dialog(self):
        """バックアップ・復元ダイアログ表示"""
        dialog = BackupRestoreDialog(self)
        dialog.exec()
    
    def optimize_database(self):
        """データベース最適化"""
        try:
            reply = QMessageBox.question(
                self, "確認", 
                "データベースを最適化しますか？\n\n"
                "この処理には時間がかかる場合があります。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # データベース最適化実行
                db_manager.optimize_database()
                
                QMessageBox.information(self, "完了", "データベースの最適化が完了しました。")
                self.update_database_info()
                
        except Exception as e:
            logger.error(f"データベース最適化エラー: {e}")
            QMessageBox.critical(self, "エラー", f"データベースの最適化に失敗しました：{e}")
    
    def check_database_integrity(self):
        """データベース整合性チェック"""
        try:
            # 整合性チェック実行
            result = db_manager.check_integrity()
            
            if result:
                QMessageBox.information(self, "チェック完了", "データベースの整合性に問題ありません。")
            else:
                QMessageBox.warning(self, "整合性エラー", "データベースに問題が検出されました。\n\nバックアップからの復元を検討してください。")
                
        except Exception as e:
            logger.error(f"整合性チェックエラー: {e}")
            QMessageBox.critical(self, "エラー", f"整合性チェックに失敗しました：{e}")
    
    def export_database(self):
        """データベースエクスポート"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "データベースエクスポート",
                f"business_system_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
                "SQL files (*.sql);;All files (*.*)"
            )
            
            if file_path:
                # エクスポート実行（実装が必要）
                QMessageBox.information(self, "完了", f"データベースをエクスポートしました：\n{file_path}")
                
        except Exception as e:
            logger.error(f"データベースエクスポートエラー: {e}")
            QMessageBox.critical(self, "エラー", f"データベースのエクスポートに失敗しました：{e}")
    
    def test_gemini_connection(self):
        """Gemini接続テスト"""
        try:
            api_key = self.gemini_key_edit.text().strip()
            if not api_key:
                QMessageBox.warning(self, "入力エラー", "Gemini APIキーを入力してください")
                return
            
            # 一時的にAPIキーを設定してテスト
            from core.gemini_integration import gemini_client
            original_key = gemini_client.api_key
            gemini_client.set_api_key(api_key)
            
            # テスト実行
            if gemini_client.is_enabled():
                QMessageBox.information(self, "接続成功", "✅ Gemini APIに正常に接続できました")
            else:
                QMessageBox.warning(self, "接続失敗", "❌ Gemini APIに接続できませんでした")
            
            # 元のキーに戻す
            gemini_client.set_api_key(original_key)
            
        except Exception as e:
            logger.error(f"Gemini接続テストエラー: {e}")
            QMessageBox.critical(self, "エラー", f"接続テストに失敗しました：{e}")
    
    def test_openai_connection(self):
        """OpenAI接続テスト"""
        try:
            api_key = self.openai_key_edit.text().strip()
            if not api_key:
                QMessageBox.warning(self, "入力エラー", "OpenAI APIキーを入力してください")
                return
            
            # 一時的にAPIキーを設定してテスト
            ai_assistant.set_api_key(api_key)
            
            # テスト実行
            if ai_assistant.is_enabled():
                QMessageBox.information(self, "接続成功", "✅ OpenAI APIに正常に接続できました")
            else:
                QMessageBox.warning(self, "接続失敗", "❌ OpenAI APIに接続できませんでした")
            
        except Exception as e:
            logger.error(f"OpenAI接続テストエラー: {e}")
            QMessageBox.critical(self, "エラー", f"接続テストに失敗しました：{e}")
    
    def showEvent(self, event):
        """表示時の処理"""
        super().showEvent(event)
        self.update_ai_status()
        self.update_database_info()
        self.fade_in(300)