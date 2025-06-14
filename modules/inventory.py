#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v4.0 - 在庫管理モジュール
商品在庫の管理、在庫レベル監視、低在庫アラート機能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QComboBox, QCheckBox, QMessageBox, QHeaderView,
    QSplitter, QGroupBox, QLabel, QDateEdit, QSpinBox,
    QDoubleSpinBox, QFrame, QScrollArea, QProgressBar, QDialog,
    QDialogButtonBox, QSlider, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QDate, QDateTime
from PyQt6.QtGui import QFont, QPixmap, QIcon, QColor
from typing import Optional, List, Dict, Any, Tuple
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path

from ui.components.base_widget import BaseWidget
from core.database import db_manager, Product
from core.config_manager import config_manager

logger = logging.getLogger(__name__)


class InventoryHistoryDialog(QDialog):
    """在庫履歴ダイアログ"""
    
    def __init__(self, product_id: int, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.setWindowTitle("在庫履歴")
        self.setModal(True)
        self.resize(800, 600)
        self.setup_ui()
        self.load_history()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # ヘッダー
        header = QLabel("📊 在庫変動履歴")
        header.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # 履歴テーブル
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "日時", "変動タイプ", "変動量", "変動後在庫", "備考", "操作者"
        ])
        
        # テーブル設定
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.history_table)
        
        # ボタン
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.close)
        layout.addWidget(button_box)
    
    def load_history(self):
        """履歴データ読み込み"""
        try:
            # 実際の実装では、在庫履歴テーブルからデータを取得
            # 今回はサンプルデータで代用
            sample_history = [
                {
                    "datetime": "2024-06-14 09:00",
                    "type": "入庫",
                    "quantity": 10,
                    "after_stock": 50,
                    "note": "新規入荷",
                    "operator": "管理者"
                },
                {
                    "datetime": "2024-06-13 15:30",
                    "type": "貸出",
                    "quantity": -3,
                    "after_stock": 40,
                    "note": "A社への貸出",
                    "operator": "田中"
                },
                {
                    "datetime": "2024-06-12 11:15",
                    "type": "返却",
                    "quantity": 2,
                    "after_stock": 43,
                    "note": "B社からの返却",
                    "operator": "佐藤"
                }
            ]
            
            self.history_table.setRowCount(len(sample_history))
            
            for row, history in enumerate(sample_history):
                self.history_table.setItem(row, 0, QTableWidgetItem(history["datetime"]))
                self.history_table.setItem(row, 1, QTableWidgetItem(history["type"]))
                self.history_table.setItem(row, 2, QTableWidgetItem(str(history["quantity"])))
                self.history_table.setItem(row, 3, QTableWidgetItem(str(history["after_stock"])))
                self.history_table.setItem(row, 4, QTableWidgetItem(history["note"]))
                self.history_table.setItem(row, 5, QTableWidgetItem(history["operator"]))
                
                # 変動タイプに応じて行の色を設定
                if history["type"] == "入庫":
                    color = QColor(220, 255, 220)  # 薄緑
                elif history["type"] == "貸出":
                    color = QColor(255, 220, 220)  # 薄赤
                else:
                    color = QColor(220, 220, 255)  # 薄青
                
                for col in range(6):
                    if self.history_table.item(row, col):
                        self.history_table.item(row, col).setBackground(color)
                        
        except Exception as e:
            logger.error(f"在庫履歴読み込みエラー: {e}")
            QMessageBox.critical(self, "エラー", f"在庫履歴の読み込みに失敗しました：{e}")


class StockAdjustmentDialog(QDialog):
    """在庫調整ダイアログ"""
    
    def __init__(self, product: Product, parent=None):
        super().__init__(parent)
        self.product = product
        self.setWindowTitle(f"在庫調整 - {product.name}")
        self.setModal(True)
        self.resize(400, 300)
        self.setup_ui()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # 現在の在庫情報
        info_group = QGroupBox("現在の在庫情報")
        info_layout = QFormLayout(info_group)
        
        self.current_stock_label = QLabel(str(self.product.stock_quantity))
        self.current_stock_label.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        info_layout.addRow("現在の在庫数:", self.current_stock_label)
        
        layout.addWidget(info_group)
        
        # 調整設定
        adjust_group = QGroupBox("在庫調整")
        adjust_layout = QFormLayout(adjust_group)
        
        self.adjustment_type = QComboBox()
        self.adjustment_type.addItems(["入庫", "出庫", "調整"])
        
        self.adjustment_quantity = QSpinBox()
        self.adjustment_quantity.setRange(-999, 999)
        self.adjustment_quantity.setValue(0)
        
        self.adjustment_reason = QTextEdit()
        self.adjustment_reason.setMaximumHeight(80)
        self.adjustment_reason.setPlaceholderText("調整理由を入力してください...")
        
        adjust_layout.addRow("調整タイプ:", self.adjustment_type)
        adjust_layout.addRow("調整数量:", self.adjustment_quantity)
        adjust_layout.addRow("調整理由:", self.adjustment_reason)
        
        layout.addWidget(adjust_group)
        
        # 調整後の予測
        self.prediction_label = QLabel()
        self.prediction_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.prediction_label)
        
        # ボタン
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # シグナル接続
        self.adjustment_quantity.valueChanged.connect(self.update_prediction)
        self.adjustment_type.currentTextChanged.connect(self.update_prediction)
        
        # 初期予測更新
        self.update_prediction()
    
    def update_prediction(self):
        """調整後の予測を更新"""
        current = self.product.stock_quantity
        adjustment = self.adjustment_quantity.value()
        
        if self.adjustment_type.currentText() == "出庫":
            adjustment = -abs(adjustment)
        elif self.adjustment_type.currentText() == "入庫":
            adjustment = abs(adjustment)
        # 調整の場合は入力された値をそのまま使用
        
        new_stock = current + adjustment
        
        if new_stock < 0:
            color = "#d73527"  # 赤
            warning = " ⚠️ 在庫がマイナスになります"
        elif new_stock <= self.product.min_stock:
            color = "#ff9800"  # オレンジ
            warning = " ⚠️ 最小在庫を下回ります"
        else:
            color = "#4caf50"  # 緑
            warning = ""
        
        self.prediction_label.setText(f"調整後在庫: {new_stock}個{warning}")
        self.prediction_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color}22;
                border: 1px solid {color};
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
                color: {color};
            }}
        """)
    
    def get_adjustment_data(self) -> Dict[str, Any]:
        """調整データを取得"""
        adjustment = self.adjustment_quantity.value()
        
        if self.adjustment_type.currentText() == "出庫":
            adjustment = -abs(adjustment)
        elif self.adjustment_type.currentText() == "入庫":
            adjustment = abs(adjustment)
        
        return {
            "product_id": self.product.id,
            "type": self.adjustment_type.currentText(),
            "quantity_change": adjustment,
            "reason": self.adjustment_reason.toPlainText(),
            "new_stock": self.product.stock_quantity + adjustment
        }


class LowStockAlertWidget(QFrame):
    """低在庫アラートウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_alerts()
        
        # 自動更新タイマー（5分ごと）
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.load_alerts)
        self.update_timer.start(300000)  # 5分
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # ヘッダー
        header_layout = QHBoxLayout()
        
        title = QLabel("⚠️ 低在庫アラート")
        title.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 更新ボタン
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("アラートを更新")
        refresh_btn.clicked.connect(self.load_alerts)
        refresh_btn.setFixedSize(30, 30)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # アラートリスト
        self.alert_list = QListWidget()
        self.alert_list.setMaximumHeight(200)
        layout.addWidget(self.alert_list)
        
        # フレームスタイル
        self.setStyleSheet("""
            LowStockAlertWidget {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 6px;
                padding: 8px;
            }
        """)
    
    def load_alerts(self):
        """アラートを読み込み"""
        try:
            self.alert_list.clear()
            
            # 低在庫商品を取得
            products = db_manager.get_all_products()
            low_stock_products = [
                p for p in products 
                if p.stock_quantity <= p.min_stock and p.min_stock > 0
            ]
            
            if not low_stock_products:
                item = QListWidgetItem("✅ 現在、低在庫商品はありません")
                item.setForeground(QColor("#4caf50"))
                self.alert_list.addItem(item)
                return
            
            for product in low_stock_products:
                if product.stock_quantity == 0:
                    text = f"🔴 {product.name}: 在庫切れ"
                    color = QColor("#d73527")
                elif product.stock_quantity <= product.min_stock / 2:
                    text = f"🟠 {product.name}: 在庫僅少 ({product.stock_quantity}個)"
                    color = QColor("#ff9800")
                else:
                    text = f"🟡 {product.name}: 低在庫 ({product.stock_quantity}個)"
                    color = QColor("#ffc107")
                
                item = QListWidgetItem(text)
                item.setForeground(color)
                item.setFont(QFont("Yu Gothic UI", 10, QFont.Weight.Bold))
                self.alert_list.addItem(item)
                
        except Exception as e:
            logger.error(f"低在庫アラート読み込みエラー: {e}")
            item = QListWidgetItem(f"❌ エラー: {str(e)}")
            item.setForeground(QColor("#d73527"))
            self.alert_list.addItem(item)


class InventoryWidget(BaseWidget):
    """在庫管理ウィジェット"""
    
    def __init__(self):
        super().__init__()
        self.current_products = []
        self.setup_ui()
        self.load_products()
        
        # 自動更新タイマー（10分ごと）
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_products)
        self.refresh_timer.start(600000)  # 10分
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # ヘッダー
        self.create_header(layout)
        
        # メインコンテンツ
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 低在庫アラート
        alert_widget = LowStockAlertWidget()
        main_splitter.addWidget(alert_widget)
        
        # 在庫一覧
        self.create_inventory_table(main_splitter)
        
        # サイズ比率設定
        main_splitter.setSizes([150, 400])
        
        layout.addWidget(main_splitter)
    
    def create_header(self, layout):
        """ヘッダー作成"""
        header_layout = QHBoxLayout()
        
        # タイトル
        title = QLabel("📦 在庫管理")
        title.setFont(QFont("Yu Gothic UI", 24, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 検索バー
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("商品名で検索...")
        self.search_edit.setMaximumWidth(200)
        self.search_edit.textChanged.connect(self.filter_products)
        header_layout.addWidget(self.search_edit)
        
        # 統計表示
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                border: 1px solid #2196f3;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(self.stats_label)
        
        # ボタン群
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 更新")
        self.refresh_btn.clicked.connect(self.load_products)
        self.refresh_btn.setStyleSheet(self.get_button_style("#2196F3"))
        button_layout.addWidget(self.refresh_btn)
        
        self.export_btn = QPushButton("📊 エクスポート")
        self.export_btn.clicked.connect(self.export_inventory)
        self.export_btn.setStyleSheet(self.get_button_style("#4CAF50"))
        button_layout.addWidget(self.export_btn)
        
        header_layout.addLayout(button_layout)
        layout.addLayout(header_layout)
    
    def create_inventory_table(self, parent):
        """在庫テーブル作成"""
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        
        # テーブルヘッダー
        table_header = QLabel("📋 在庫一覧")
        table_header.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
        table_layout.addWidget(table_header)
        
        # テーブル
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(8)
        self.inventory_table.setHorizontalHeaderLabels([
            "商品名", "現在庫数", "最小在庫", "最大在庫", "在庫レベル", "状態", "最終更新", "操作"
        ])
        
        # テーブル設定
        header = self.inventory_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        
        self.inventory_table.setAlternatingRowColors(True)
        self.inventory_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        table_layout.addWidget(self.inventory_table)
        parent.addWidget(table_widget)
    
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
                background-color: {color};
                background-color: #1976D2;
            }}
        """
    
    def load_products(self):
        """商品データ読み込み"""
        try:
            self.current_products = db_manager.get_all_products()
            self.update_table()
            self.update_statistics()
            
        except Exception as e:
            logger.error(f"商品データ読み込みエラー: {e}")
            QMessageBox.critical(self, "エラー", f"商品データの読み込みに失敗しました：{e}")
    
    def update_table(self):
        """テーブル更新"""
        try:
            products = self.current_products
            
            self.inventory_table.setRowCount(len(products))
            
            for row, product in enumerate(products):
                # 商品名
                self.inventory_table.setItem(row, 0, QTableWidgetItem(product.name))
                
                # 現在庫数
                stock_item = QTableWidgetItem(str(product.stock_quantity))
                if product.stock_quantity == 0:
                    stock_item.setBackground(QColor("#ffebee"))  # 薄赤
                elif product.stock_quantity <= product.min_stock:
                    stock_item.setBackground(QColor("#fff3e0"))  # 薄オレンジ
                else:
                    stock_item.setBackground(QColor("#e8f5e8"))  # 薄緑
                self.inventory_table.setItem(row, 1, stock_item)
                
                # 最小在庫
                self.inventory_table.setItem(row, 2, QTableWidgetItem(str(product.min_stock)))
                
                # 最大在庫（仮の値）
                max_stock = product.min_stock * 3 if product.min_stock > 0 else 100
                self.inventory_table.setItem(row, 3, QTableWidgetItem(str(max_stock)))
                
                # 在庫レベル（プログレスバー風）
                level_widget = QWidget()
                level_layout = QHBoxLayout(level_widget)
                level_layout.setContentsMargins(4, 4, 4, 4)
                
                if product.min_stock > 0:
                    level_percentage = min(100, (product.stock_quantity / (max_stock)) * 100)
                else:
                    level_percentage = 50  # デフォルト
                
                level_bar = QProgressBar()
                level_bar.setMaximum(100)
                level_bar.setValue(int(level_percentage))
                level_bar.setFormat(f"{level_percentage:.0f}%")
                
                if level_percentage <= 25:
                    level_bar.setStyleSheet("QProgressBar::chunk { background-color: #f44336; }")
                elif level_percentage <= 50:
                    level_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff9800; }")
                else:
                    level_bar.setStyleSheet("QProgressBar::chunk { background-color: #4caf50; }")
                
                level_layout.addWidget(level_bar)
                self.inventory_table.setCellWidget(row, 4, level_widget)
                
                # 状態
                if product.stock_quantity == 0:
                    status = "在庫切れ"
                    status_color = QColor("#f44336")
                elif product.stock_quantity <= product.min_stock:
                    status = "低在庫"
                    status_color = QColor("#ff9800")
                else:
                    status = "正常"
                    status_color = QColor("#4caf50")
                
                status_item = QTableWidgetItem(status)
                status_item.setForeground(status_color)
                status_item.setFont(QFont("Yu Gothic UI", 10, QFont.Weight.Bold))
                self.inventory_table.setItem(row, 5, status_item)
                
                # 最終更新（仮の値）
                last_update = datetime.now().strftime("%m-%d %H:%M")
                self.inventory_table.setItem(row, 6, QTableWidgetItem(last_update))
                
                # 操作ボタン
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(2, 2, 2, 2)
                
                # 調整ボタン
                adjust_btn = QPushButton("調整")
                adjust_btn.setStyleSheet(self.get_button_style("#2196F3"))
                adjust_btn.setFixedSize(50, 25)
                adjust_btn.clicked.connect(lambda checked, p=product: self.adjust_stock(p))
                action_layout.addWidget(adjust_btn)
                
                # 履歴ボタン
                history_btn = QPushButton("履歴")
                history_btn.setStyleSheet(self.get_button_style("#9c27b0"))
                history_btn.setFixedSize(50, 25)
                history_btn.clicked.connect(lambda checked, p=product: self.show_history(p))
                action_layout.addWidget(history_btn)
                
                self.inventory_table.setCellWidget(row, 7, action_widget)
                
        except Exception as e:
            logger.error(f"テーブル更新エラー: {e}")
    
    def update_statistics(self):
        """統計情報更新"""
        try:
            total_products = len(self.current_products)
            total_stock = sum(p.stock_quantity for p in self.current_products)
            low_stock_count = len([p for p in self.current_products if p.stock_quantity <= p.min_stock and p.min_stock > 0])
            out_of_stock_count = len([p for p in self.current_products if p.stock_quantity == 0])
            
            stats_text = f"総商品数: {total_products} | 総在庫数: {total_stock} | 低在庫: {low_stock_count} | 在庫切れ: {out_of_stock_count}"
            self.stats_label.setText(stats_text)
            
            # 状態に応じて色を変更
            if out_of_stock_count > 0:
                color = "#f44336"
            elif low_stock_count > 0:
                color = "#ff9800"
            else:
                color = "#4caf50"
            
            self.stats_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {color}22;
                    border: 1px solid {color};
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                    color: {color};
                }}
            """)
            
        except Exception as e:
            logger.error(f"統計更新エラー: {e}")
    
    def filter_products(self):
        """商品フィルタリング"""
        search_text = self.search_edit.text().lower()
        
        for row in range(self.inventory_table.rowCount()):
            item = self.inventory_table.item(row, 0)  # 商品名
            if item:
                visible = search_text in item.text().lower()
                self.inventory_table.setRowHidden(row, not visible)
    
    def adjust_stock(self, product: Product):
        """在庫調整"""
        try:
            dialog = StockAdjustmentDialog(product, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                adjustment_data = dialog.get_adjustment_data()
                
                # データベース更新
                product.stock_quantity = adjustment_data["new_stock"]
                db_manager.update_product(product)
                
                # ここで在庫履歴も記録すべき（実装時に追加）
                
                # テーブル更新
                self.load_products()
                
                QMessageBox.information(
                    self, "完了", 
                    f"在庫調整が完了しました。\n"
                    f"商品: {product.name}\n"
                    f"調整量: {adjustment_data['quantity_change']}\n"
                    f"調整後在庫: {adjustment_data['new_stock']}"
                )
                
        except Exception as e:
            logger.error(f"在庫調整エラー: {e}")
            QMessageBox.critical(self, "エラー", f"在庫調整に失敗しました：{e}")
    
    def show_history(self, product: Product):
        """在庫履歴表示"""
        try:
            dialog = InventoryHistoryDialog(product.id, self)
            dialog.exec()
            
        except Exception as e:
            logger.error(f"履歴表示エラー: {e}")
            QMessageBox.critical(self, "エラー", f"履歴表示に失敗しました：{e}")
    
    def export_inventory(self):
        """在庫データエクスポート"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            # ファイル保存ダイアログ
            file_path, _ = QFileDialog.getSaveFileName(
                self, "在庫データエクスポート", 
                f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV files (*.csv);;Excel files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # CSVエクスポート
            if file_path.endswith('.csv'):
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([
                        "商品名", "現在庫数", "最小在庫", "単価", "状態", "最終更新"
                    ])
                    
                    for product in self.current_products:
                        if product.stock_quantity == 0:
                            status = "在庫切れ"
                        elif product.stock_quantity <= product.min_stock:
                            status = "低在庫"
                        else:
                            status = "正常"
                        
                        writer.writerow([
                            product.name,
                            product.stock_quantity,
                            product.min_stock,
                            product.unit_price,
                            status,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ])
            
            QMessageBox.information(self, "完了", f"在庫データをエクスポートしました：\n{file_path}")
            
        except Exception as e:
            logger.error(f"エクスポートエラー: {e}")
            QMessageBox.critical(self, "エラー", f"エクスポートに失敗しました：{e}")
    
    def showEvent(self, event):
        """表示時の処理"""
        super().showEvent(event)
        self.fade_in(300)