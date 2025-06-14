#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v3.0 - プラグインマネージャーダイアログ
プラグインの有効/無効切り替え、インストール、管理
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QTextEdit, QSplitter, QGroupBox, QCheckBox,
    QMessageBox, QHeaderView, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QProgressBar, QFileDialog, QLineEdit, QComboBox, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

from core.plugin_manager import PluginManager, PluginInfo, PluginInterface

logger = logging.getLogger(__name__)


class PluginInfoWidget(QLabel):
    """プラグイン情報表示ウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWordWrap(True)
        self.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 15px;
                font-family: "Yu Gothic UI";
            }
        """)
        self.clear_info()
    
    def set_plugin_info(self, plugin_info: PluginInfo, is_loaded: bool = False):
        """プラグイン情報を設定"""
        status_color = "#28a745" if is_loaded else "#6c757d"
        status_text = "読み込み済み" if is_loaded else "未読み込み"
        
        enabled_color = "#28a745" if plugin_info.enabled else "#dc3545"
        enabled_text = "有効" if plugin_info.enabled else "無効"
        
        info_html = f"""
        <h3 style="color: #2196F3; margin-top: 0;">{plugin_info.name}</h3>
        
        <p><strong>バージョン:</strong> {plugin_info.version}</p>
        <p><strong>作者:</strong> {plugin_info.author}</p>
        <p><strong>カテゴリ:</strong> {plugin_info.category}</p>
        <p><strong>状態:</strong> 
           <span style="color: {status_color};">●</span> {status_text} / 
           <span style="color: {enabled_color};">●</span> {enabled_text}
        </p>
        
        <h4 style="color: #495057;">説明</h4>
        <p>{plugin_info.description}</p>
        
        <h4 style="color: #495057;">技術情報</h4>
        <p><strong>モジュール:</strong> {plugin_info.module_name}</p>
        <p><strong>メインクラス:</strong> {plugin_info.main_class}</p>
        
        <h4 style="color: #495057;">依存関係</h4>
        <p>{', '.join(plugin_info.dependencies) if plugin_info.dependencies else 'なし'}</p>
        """
        
        self.setText(info_html)
    
    def clear_info(self):
        """情報クリア"""
        self.setText("""
        <div style="text-align: center; color: #6c757d; margin-top: 50px;">
            <h3>プラグインを選択してください</h3>
            <p>プラグインの詳細情報がここに表示されます</p>
        </div>
        """)


class PluginListWidget(QTableWidget):
    """プラグイン一覧ウィジェット"""
    
    # シグナル
    plugin_selected = pyqtSignal(str)  # plugin_name
    plugin_toggled = pyqtSignal(str, bool)  # plugin_name, enabled
    
    def __init__(self, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.setup_ui()
        self.setup_connections()
        self.refresh_list()
    
    def setup_ui(self):
        """UI設定"""
        # ヘッダー設定
        headers = ["有効", "名前", "バージョン", "カテゴリ", "作者", "状態", "説明"]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # テーブル設定
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # ヘッダーサイズ調整
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 有効
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 名前
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # バージョン
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # カテゴリ
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 作者
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 状態
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # 説明
    
    def setup_connections(self):
        """シグナル接続"""
        self.itemSelectionChanged.connect(self.on_selection_changed)
        self.cellChanged.connect(self.on_cell_changed)
    
    def refresh_list(self):
        """一覧更新"""
        try:
            # 利用可能なプラグインをスキャン
            available_plugins = self.plugin_manager.scan_plugins()
            loaded_plugins = self.plugin_manager.get_all_plugins()
            
            # テーブル設定
            self.setRowCount(len(available_plugins))
            
            for row, plugin_info in enumerate(available_plugins):
                # 有効/無効チェックボックス
                checkbox = QCheckBox()
                checkbox.setChecked(plugin_info.enabled)
                checkbox.stateChanged.connect(
                    lambda state, name=plugin_info.name: 
                    self.plugin_toggled.emit(name, state == Qt.CheckState.Checked)
                )
                self.setCellWidget(row, 0, checkbox)
                
                # 基本情報
                self.setItem(row, 1, QTableWidgetItem(plugin_info.name))
                self.setItem(row, 2, QTableWidgetItem(plugin_info.version))
                self.setItem(row, 3, QTableWidgetItem(plugin_info.category))
                self.setItem(row, 4, QTableWidgetItem(plugin_info.author))
                
                # 状態
                is_loaded = plugin_info.name in loaded_plugins
                status_text = "読み込み済み" if is_loaded else "未読み込み"
                status_item = QTableWidgetItem(status_text)
                
                if is_loaded:
                    status_item.setBackground(Qt.GlobalColor.lightGreen)
                else:
                    status_item.setBackground(Qt.GlobalColor.lightGray)
                
                self.setItem(row, 5, status_item)
                
                # 説明
                description = plugin_info.description[:50] + "..." if len(plugin_info.description) > 50 else plugin_info.description
                self.setItem(row, 6, QTableWidgetItem(description))
                
                # プラグイン情報を行データとして保存
                self.item(row, 1).setData(Qt.ItemDataRole.UserRole, plugin_info)
            
        except Exception as e:
            logger.error(f"プラグイン一覧更新エラー: {e}")
    
    def on_selection_changed(self):
        """選択変更時"""
        current_row = self.currentRow()
        if current_row >= 0:
            item = self.item(current_row, 1)
            if item:
                plugin_info = item.data(Qt.ItemDataRole.UserRole)
                if plugin_info:
                    self.plugin_selected.emit(plugin_info.name)
    
    def on_cell_changed(self, row: int, column: int):
        """セル変更時"""
        # 必要に応じて処理追加
        pass
    
    def get_selected_plugin(self) -> Optional[PluginInfo]:
        """選択されたプラグイン情報を取得"""
        current_row = self.currentRow()
        if current_row >= 0:
            item = self.item(current_row, 1)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None


class PluginManagerDialog(QDialog):
    """プラグインマネージャーダイアログ"""
    
    def __init__(self, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.setup_ui()
        self.setup_connections()
        self.setWindowTitle("プラグインマネージャー")
        self.resize(800, 600)
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        
        # メインタブ
        main_tab = QWidget()
        self.setup_main_tab(main_tab)
        self.tab_widget.addTab(main_tab, "プラグイン管理")
        
        # インストールタブ
        install_tab = QWidget()
        self.setup_install_tab(install_tab)
        self.tab_widget.addTab(install_tab, "インストール")
        
        layout.addWidget(self.tab_widget)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.refresh_btn = QPushButton("更新")
        self.close_btn = QPushButton("閉じる")
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def setup_main_tab(self, tab_widget: QWidget):
        """メインタブ設定"""
        layout = QVBoxLayout(tab_widget)
        
        # スプリッター
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左側: プラグイン一覧
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 一覧ヘッダー
        list_header = QLabel("利用可能なプラグイン")
        list_header.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        left_layout.addWidget(list_header)
        
        # フィルタ
        filter_layout = QHBoxLayout()
        self.category_filter = QComboBox()
        self.category_filter.addItem("すべてのカテゴリ", "")
        self.category_filter.addItem("業務機能", "business")
        self.category_filter.addItem("レポート", "report")
        self.category_filter.addItem("ツール", "tool")
        self.category_filter.addItem("サンプル", "sample")
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("プラグイン名で検索...")
        
        filter_layout.addWidget(QLabel("カテゴリ:"))
        filter_layout.addWidget(self.category_filter)
        filter_layout.addWidget(QLabel("検索:"))
        filter_layout.addWidget(self.search_edit)
        
        left_layout.addLayout(filter_layout)
        
        # プラグイン一覧
        self.plugin_list = PluginListWidget(self.plugin_manager)
        left_layout.addWidget(self.plugin_list)
        
        # 操作ボタン
        button_layout = QHBoxLayout()
        self.enable_btn = QPushButton("有効化")
        self.disable_btn = QPushButton("無効化")
        self.reload_btn = QPushButton("再読み込み")
        self.uninstall_btn = QPushButton("アンインストール")
        
        button_layout.addWidget(self.enable_btn)
        button_layout.addWidget(self.disable_btn)
        button_layout.addWidget(self.reload_btn)
        button_layout.addWidget(self.uninstall_btn)
        button_layout.addStretch()
        
        left_layout.addLayout(button_layout)
        
        splitter.addWidget(left_widget)
        
        # 右側: プラグイン詳細
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 詳細ヘッダー
        detail_header = QLabel("プラグイン詳細")
        detail_header.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        right_layout.addWidget(detail_header)
        
        # 詳細情報
        self.plugin_info_widget = PluginInfoWidget()
        right_layout.addWidget(self.plugin_info_widget)
        
        splitter.addWidget(right_widget)
        
        # スプリッター比率設定
        splitter.setSizes([500, 300])
        
        layout.addWidget(splitter)
    
    def setup_install_tab(self, tab_widget: QWidget):
        """インストールタブ設定"""
        layout = QVBoxLayout(tab_widget)
        
        # インストールグループ
        install_group = QGroupBox("新しいプラグインのインストール")
        install_layout = QVBoxLayout(install_group)
        
        # ファイルからインストール
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("プラグインファイル（.zip）を選択してください")
        self.browse_btn = QPushButton("参照...")
        self.install_btn = QPushButton("インストール")
        
        file_layout.addWidget(QLabel("ファイル:"))
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(self.browse_btn)
        file_layout.addWidget(self.install_btn)
        
        install_layout.addLayout(file_layout)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        install_layout.addWidget(self.progress_bar)
        
        # インストールログ
        self.install_log = QTextEdit()
        self.install_log.setMaximumHeight(200)
        self.install_log.setPlaceholderText("インストールの進行状況がここに表示されます...")
        install_layout.addWidget(self.install_log)
        
        layout.addWidget(install_group)
        
        # オンラインリポジトリ（将来実装）
        online_group = QGroupBox("オンラインリポジトリ（将来実装）")
        online_layout = QVBoxLayout(online_group)
        
        online_info = QLabel(
            "将来のバージョンでは、オンラインリポジトリから\n"
            "プラグインを直接ダウンロード・インストールできるようになります。"
        )
        online_info.setStyleSheet("color: #6c757d; font-style: italic;")
        online_layout.addWidget(online_info)
        
        layout.addWidget(online_group)
        
        layout.addStretch()
    
    def setup_connections(self):
        """シグナル接続"""
        # メインタブ
        self.plugin_list.plugin_selected.connect(self.on_plugin_selected)
        self.plugin_list.plugin_toggled.connect(self.on_plugin_toggled)
        
        self.enable_btn.clicked.connect(self.enable_plugin)
        self.disable_btn.clicked.connect(self.disable_plugin)
        self.reload_btn.clicked.connect(self.reload_plugin)
        self.uninstall_btn.clicked.connect(self.uninstall_plugin)
        
        self.category_filter.currentTextChanged.connect(self.filter_plugins)
        self.search_edit.textChanged.connect(self.filter_plugins)
        
        # インストールタブ
        self.browse_btn.clicked.connect(self.browse_plugin_file)
        self.install_btn.clicked.connect(self.install_plugin)
        
        # ダイアログ
        self.refresh_btn.clicked.connect(self.refresh_all)
        self.close_btn.clicked.connect(self.accept)
        
        # プラグインマネージャーのシグナル
        self.plugin_manager.plugin_loaded.connect(self.on_plugin_loaded)
        self.plugin_manager.plugin_unloaded.connect(self.on_plugin_unloaded)
        self.plugin_manager.plugin_error.connect(self.on_plugin_error)
    
    def on_plugin_selected(self, plugin_name: str):
        """プラグイン選択時"""
        try:
            plugin_info = self.plugin_manager.get_plugin_info(plugin_name)
            if plugin_info:
                is_loaded = plugin_name in self.plugin_manager.get_all_plugins()
                self.plugin_info_widget.set_plugin_info(plugin_info, is_loaded)
        except Exception as e:
            logger.error(f"プラグイン選択エラー: {e}")
    
    def on_plugin_toggled(self, plugin_name: str, enabled: bool):
        """プラグイン有効/無効切り替え"""
        try:
            if enabled:
                self.plugin_manager.enable_plugin(plugin_name)
            else:
                self.plugin_manager.disable_plugin(plugin_name)
            
            self.plugin_list.refresh_list()
            
        except Exception as e:
            logger.error(f"プラグイン切り替えエラー: {e}")
            QMessageBox.critical(self, "エラー", f"プラグインの切り替えに失敗しました:\n{str(e)}")
    
    def enable_plugin(self):
        """プラグイン有効化"""
        plugin_info = self.plugin_list.get_selected_plugin()
        if plugin_info:
            success = self.plugin_manager.enable_plugin(plugin_info.name)
            if success:
                self.plugin_list.refresh_list()
                QMessageBox.information(self, "成功", f"プラグイン '{plugin_info.name}' を有効化しました。")
    
    def disable_plugin(self):
        """プラグイン無効化"""
        plugin_info = self.plugin_list.get_selected_plugin()
        if plugin_info:
            success = self.plugin_manager.disable_plugin(plugin_info.name)
            if success:
                self.plugin_list.refresh_list()
                QMessageBox.information(self, "成功", f"プラグイン '{plugin_info.name}' を無効化しました。")
    
    def reload_plugin(self):
        """プラグイン再読み込み"""
        plugin_info = self.plugin_list.get_selected_plugin()
        if plugin_info:
            success = self.plugin_manager.reload_plugin(plugin_info.name)
            if success:
                self.plugin_list.refresh_list()
                QMessageBox.information(self, "成功", f"プラグイン '{plugin_info.name}' を再読み込みしました。")
    
    def uninstall_plugin(self):
        """プラグインアンインストール"""
        plugin_info = self.plugin_list.get_selected_plugin()
        if not plugin_info:
            return
        
        reply = QMessageBox.question(
            self, "確認",
            f"プラグイン '{plugin_info.name}' をアンインストールしますか？\n"
            "この操作は元に戻せません。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # アンインストール処理（将来実装）
            QMessageBox.information(self, "情報", "アンインストール機能は将来のバージョンで実装予定です。")
    
    def filter_plugins(self):
        """プラグインフィルタ"""
        # フィルタ機能（将来実装）
        pass
    
    def browse_plugin_file(self):
        """プラグインファイル選択"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "プラグインファイルを選択",
            "", "プラグインファイル (*.zip);;すべてのファイル (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
    
    def install_plugin(self):
        """プラグインインストール"""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "入力エラー", "プラグインファイルを選択してください。")
            return
        
        if not Path(file_path).exists():
            QMessageBox.warning(self, "ファイルエラー", "指定されたファイルが見つかりません。")
            return
        
        # インストール処理（将来実装）
        QMessageBox.information(self, "情報", "プラグインインストール機能は将来のバージョンで実装予定です。")
    
    def refresh_all(self):
        """すべて更新"""
        self.plugin_list.refresh_list()
        self.plugin_info_widget.clear_info()
    
    def on_plugin_loaded(self, plugin_name: str):
        """プラグイン読み込み完了時"""
        self.plugin_list.refresh_list()
        self.install_log.append(f"✓ プラグイン '{plugin_name}' を読み込みました。")
    
    def on_plugin_unloaded(self, plugin_name: str):
        """プラグインアンロード完了時"""
        self.plugin_list.refresh_list()
        self.install_log.append(f"○ プラグイン '{plugin_name}' をアンロードしました。")
    
    def on_plugin_error(self, plugin_name: str, error_message: str):
        """プラグインエラー時"""
        self.install_log.append(f"✗ プラグイン '{plugin_name}' でエラー: {error_message}")
        QMessageBox.critical(self, "プラグインエラー", 
                           f"プラグイン '{plugin_name}' でエラーが発生しました:\n{error_message}")