#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v4.0 - ハイブリッドAI設定ダイアログ
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QPushButton, QLabel, QGroupBox,
    QMessageBox, QTableWidget, QTableWidgetItem, QCheckBox, 
    QDoubleSpinBox, QHeaderView, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Any
import logging

from core.hybrid_ai_system import AIProvider, AITaskType

logger = logging.getLogger(__name__)


class HybridAISettingsDialog(QDialog):
    """ハイブリッドAI設定ダイアログ"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, hybrid_manager, parent=None):
        super().__init__(parent)
        self.hybrid_manager = hybrid_manager
        self.setup_ui()
        self.load_current_settings()
        self.update_status_display()
    
    def setup_ui(self):
        """UI設定"""
        self.setWindowTitle("ハイブリッドAIシステム設定")
        self.setModal(True)
        self.resize(700, 800)
        
        layout = QVBoxLayout(self)
        
        # タイトル
        title = QLabel("🔄 ハイブリッドAIシステム設定")
        title.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2196F3; margin: 10px 0;")
        layout.addWidget(title)
        
        # プロバイダー設定グループ
        provider_group = QGroupBox("AIプロバイダー設定")
        provider_layout = QFormLayout(provider_group)
        
        self.preferred_provider_combo = QComboBox()
        self.preferred_provider_combo.addItems([
            "自動選択 (推奨)",
            "Gemini優先", 
            "OpenAI優先"
        ])
        
        self.fallback_check = QCheckBox("フォールバック機能を有効にする")
        self.fallback_check.setChecked(True)
        self.fallback_check.setToolTip("プライマリプロバイダーが失敗した場合、自動的に別のプロバイダーに切り替え")
        
        provider_layout.addRow("優先プロバイダー:", self.preferred_provider_combo)
        provider_layout.addRow("", self.fallback_check)
        
        layout.addWidget(provider_group)
        
        # コスト管理グループ
        cost_group = QGroupBox("コスト管理")
        cost_layout = QFormLayout(cost_group)
        
        self.cost_limit_spin = QDoubleSpinBox()
        self.cost_limit_spin.setRange(0.0, 1000.0)
        self.cost_limit_spin.setValue(50.0)
        self.cost_limit_spin.setSuffix(" USD")
        self.cost_limit_spin.setDecimals(2)
        
        self.cost_optimization_check = QCheckBox("コスト最適化を有効にする")
        self.cost_optimization_check.setChecked(True)
        self.cost_optimization_check.setToolTip("タスクに応じて最もコスト効率の良いAIを自動選択")
        
        cost_layout.addRow("月間コスト制限:", self.cost_limit_spin)
        cost_layout.addRow("", self.cost_optimization_check)
        
        layout.addWidget(cost_group)
        
        # タスク配分設定
        task_group = QGroupBox("タスク別AI配分設定")
        task_layout = QVBoxLayout(task_group)
        
        # タスク配分テーブル
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(3)
        self.task_table.setHorizontalHeaderLabels(["タスクタイプ", "優先AI", "説明"])
        
        # テーブルの列幅設定
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.task_table.setColumnWidth(0, 150)
        self.task_table.setColumnWidth(1, 120)
        
        self.populate_task_table()
        
        task_layout.addWidget(self.task_table)
        layout.addWidget(task_group)
        
        # ステータス表示
        status_group = QGroupBox("システム状況")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        
        self.refresh_status_btn = QPushButton("🔄 状況更新")
        self.refresh_status_btn.clicked.connect(self.update_status_display)
        
        status_layout.addWidget(self.status_text)
        status_layout.addWidget(self.refresh_status_btn)
        
        layout.addWidget(status_group)
        
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
        
        self.reset_btn = QPushButton("🔄 リセット")
        self.reset_btn.setStyleSheet("""
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
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # シグナル接続
        self.save_btn.clicked.connect(self.save_settings)
        self.reset_btn.clicked.connect(self.reset_settings)
        self.cancel_btn.clicked.connect(self.reject)
    
    def populate_task_table(self):
        """タスク配分テーブル設定"""
        task_info = [
            ("画像分析", "Gemini", "画像・文書の分析・OCR処理"),
            ("データ分析", "Gemini", "大容量データの分析・統計処理"),
            ("テキスト生成", "OpenAI", "自然言語生成・文章作成"),
            ("コード生成", "OpenAI", "プログラミング・スクリプト生成"),
            ("チャット", "OpenAI", "リアルタイム会話・質問応答"),
            ("翻訳", "自動選択", "多言語翻訳処理"),
            ("要約", "自動選択", "文書・データの要約"),
            ("マルチモーダル", "Gemini", "画像+テキストの複合処理")
        ]
        
        self.task_table.setRowCount(len(task_info))
        
        for row, (task, ai, description) in enumerate(task_info):
            # タスクタイプ
            task_item = QTableWidgetItem(task)
            task_item.setFlags(task_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.task_table.setItem(row, 0, task_item)
            
            # AI選択コンボボックス
            ai_combo = QComboBox()
            ai_combo.addItems(["自動選択", "Gemini", "OpenAI"])
            ai_combo.setCurrentText(ai)
            self.task_table.setCellWidget(row, 1, ai_combo)
            
            # 説明
            desc_item = QTableWidgetItem(description)
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.task_table.setItem(row, 2, desc_item)
    
    def load_current_settings(self):
        """現在の設定を読み込み"""
        try:
            # プロバイダー設定
            provider_map = {
                AIProvider.AUTO: "自動選択 (推奨)",
                AIProvider.GEMINI: "Gemini優先",
                AIProvider.OPENAI: "OpenAI優先"
            }
            
            current_provider = provider_map.get(
                self.hybrid_manager.preferred_provider, 
                "自動選択 (推奨)"
            )
            
            index = self.preferred_provider_combo.findText(current_provider)
            if index >= 0:
                self.preferred_provider_combo.setCurrentIndex(index)
            
            # フォールバック設定
            self.fallback_check.setChecked(self.hybrid_manager.fallback_enabled)
            
            # コスト設定
            self.cost_limit_spin.setValue(self.hybrid_manager.monthly_cost_limit)
            
        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
    
    def update_status_display(self):
        """ステータス表示更新"""
        try:
            status_report = self.hybrid_manager.get_status_report()
            
            status_text = []
            status_text.append("=== ハイブリッドAIシステム状況 ===\n")
            
            # プロバイダー状況
            status_text.append("【AIプロバイダー状況】")
            
            openai_status = status_report["providers"]["openai"]
            if openai_status["enabled"]:
                stats = openai_status["stats"]
                status_text.append(f"✅ OpenAI: 利用可能")
                status_text.append(f"   📊 リクエスト数: {stats['requests']}")
                status_text.append(f"   ✅ 成功率: {stats['successes']}/{stats['requests']}")
                status_text.append(f"   ⏱️ 平均応答時間: {stats['avg_response_time']:.2f}秒")
            else:
                status_text.append("❌ OpenAI: 利用不可")
            
            gemini_status = status_report["providers"]["gemini"]
            if gemini_status["enabled"]:
                status_text.append(f"✅ Gemini: 利用可能")
                status_text.append(f"   📊 月間使用量: {gemini_status['usage']:,} トークン")
                status_text.append(f"   💾 残り制限: {gemini_status['remaining']:,} トークン")
                stats = gemini_status["stats"]
                status_text.append(f"   📈 リクエスト数: {stats['requests']}")
                status_text.append(f"   ✅ 成功率: {stats['successes']}/{stats['requests']}")
            else:
                status_text.append("❌ Gemini: 利用不可")
            
            # コスト情報
            cost_info = status_report["cost"]
            status_text.append(f"\n【コスト管理】")
            status_text.append(f"💰 月間コスト: ${cost_info['current_monthly']:.2f}")
            status_text.append(f"🎯 コスト制限: ${cost_info['limit']:.2f}")
            status_text.append(f"📊 使用率: {cost_info['percentage']:.1f}%")
            
            # 設定情報
            settings_info = status_report["settings"]
            status_text.append(f"\n【現在の設定】")
            status_text.append(f"🤖 優先プロバイダー: {settings_info['preferred_provider']}")
            status_text.append(f"🔄 フォールバック: {'有効' if settings_info['fallback_enabled'] else '無効'}")
            
            self.status_text.setPlainText("\n".join(status_text))
            
        except Exception as e:
            logger.error(f"ステータス更新エラー: {e}")
            self.status_text.setPlainText(f"ステータス取得エラー: {str(e)}")
    
    def save_settings(self):
        """設定保存"""
        try:
            # プロバイダー設定
            provider_map = {
                "自動選択 (推奨)": AIProvider.AUTO,
                "Gemini優先": AIProvider.GEMINI,
                "OpenAI優先": AIProvider.OPENAI
            }
            
            selected_provider = self.preferred_provider_combo.currentText()
            self.hybrid_manager.preferred_provider = provider_map.get(
                selected_provider, AIProvider.AUTO
            )
            
            # その他の設定
            self.hybrid_manager.fallback_enabled = self.fallback_check.isChecked()
            self.hybrid_manager.monthly_cost_limit = self.cost_limit_spin.value()
            
            # 設定保存
            self.hybrid_manager.save_settings()
            
            QMessageBox.information(self, "設定保存", "ハイブリッドAI設定を保存しました。")
            self.settings_changed.emit()
            self.accept()
            
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"設定保存に失敗しました:\n{str(e)}")
    
    def reset_settings(self):
        """設定リセット"""
        reply = QMessageBox.question(
            self, "設定リセット",
            "設定をデフォルト値にリセットしますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # デフォルト値に戻す
            self.preferred_provider_combo.setCurrentText("自動選択 (推奨)")
            self.fallback_check.setChecked(True)
            self.cost_limit_spin.setValue(50.0)
            self.cost_optimization_check.setChecked(True)
            
            # テーブルもリセット
            self.populate_task_table()
            
            QMessageBox.information(self, "リセット完了", "設定をデフォルト値にリセットしました。")