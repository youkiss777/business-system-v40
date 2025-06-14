#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v3.0 - 商品管理モジュール
PyQt6ベースの商品管理機能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QComboBox, QCheckBox, QMessageBox, QHeaderView,
    QSplitter, QGroupBox, QLabel, QDoubleSpinBox, QSpinBox,
    QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon
from typing import Optional, List, Dict, Any
import logging

from core.database import Product, db_manager
from ui.components.base_widget import BaseWidget
from ui.components.form_header import FormHeaderWidget, ActionButton

logger = logging.getLogger(__name__)


class ProductFormWidget(BaseWidget):
    """商品入力フォームウィジェット"""
    
    # シグナル
    product_saved = pyqtSignal(str)  # product_id
    product_updated = pyqtSignal(str)
    product_deleted = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_product_id: Optional[str] = None
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # 基本情報グループ
        basic_group = QGroupBox("基本情報")
        basic_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        basic_group.setMinimumWidth(950)  # グループの最小幅を大幅拡大
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(15)
        basic_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        self.product_id_edit = QLineEdit()
        self.product_id_edit.setPlaceholderText("自動採番されます")
        self.product_id_edit.setMinimumHeight(40)
        self.product_id_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px; background-color: #f5f5f5;")
        self.product_id_edit.setReadOnly(True)  # 読み取り専用に設定
        basic_layout.addRow("商品ID:", self.product_id_edit)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("商品名を入力してください")
        self.name_edit.setMinimumHeight(40)
        self.name_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        basic_layout.addRow("商品名 *:", self.name_edit)
        
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("型番・モデル名")
        self.model_edit.setMinimumHeight(40)
        self.model_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        basic_layout.addRow("型番:", self.model_edit)
        
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setMinimumHeight(40)
        self.category_combo.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        self.category_combo.addItems([
            "プロジェクター", "スクリーン", "音響機器", "照明機器",
            "カメラ", "PC・タブレット", "その他"
        ])
        basic_layout.addRow("カテゴリ:", self.category_combo)
        
        layout.addWidget(basic_group)
        
        # 価格設定グループ
        price_group = QGroupBox("価格設定")
        price_group.setFont(QFont("Yu Gothic UI", 10, QFont.Weight.Bold))
        price_layout = QFormLayout(price_group)
        price_layout.setSpacing(12)
        
        # 日単価
        daily_layout = QHBoxLayout()
        self.daily_rate_spin = QDoubleSpinBox()
        self.daily_rate_spin.setRange(0, 999999)
        self.daily_rate_spin.setDecimals(0)
        self.daily_rate_spin.setSuffix(" 円")
        daily_layout.addWidget(self.daily_rate_spin)
        daily_layout.addStretch()
        price_layout.addRow("日単価 *:", daily_layout)
        
        # 月単価
        monthly_layout = QHBoxLayout()
        self.monthly_rate_spin = QDoubleSpinBox()
        self.monthly_rate_spin.setRange(0, 999999)
        self.monthly_rate_spin.setDecimals(0)
        self.monthly_rate_spin.setSuffix(" 円")
        monthly_layout.addWidget(self.monthly_rate_spin)
        monthly_layout.addStretch()
        price_layout.addRow("月単価:", monthly_layout)
        
        # 破損料金
        damage_layout = QHBoxLayout()
        self.damage_rate_spin = QDoubleSpinBox()
        self.damage_rate_spin.setRange(0, 999999)
        self.damage_rate_spin.setDecimals(0)
        self.damage_rate_spin.setSuffix(" 円")
        damage_layout.addWidget(self.damage_rate_spin)
        damage_layout.addStretch()
        price_layout.addRow("破損料金:", damage_layout)
        
        layout.addWidget(price_group)
        
        # 在庫情報グループ
        stock_group = QGroupBox("在庫情報")
        stock_group.setFont(QFont("Yu Gothic UI", 10, QFont.Weight.Bold))
        stock_layout = QFormLayout(stock_group)
        stock_layout.setSpacing(12)
        
        # 現在庫
        current_stock_layout = QHBoxLayout()
        self.current_stock_spin = QSpinBox()
        self.current_stock_spin.setRange(0, 9999)
        self.current_stock_spin.setSuffix(" 個")
        current_stock_layout.addWidget(self.current_stock_spin)
        current_stock_layout.addStretch()
        stock_layout.addRow("現在庫数:", current_stock_layout)
        
        # 最低在庫
        min_stock_layout = QHBoxLayout()
        self.min_stock_spin = QSpinBox()
        self.min_stock_spin.setRange(0, 9999)
        self.min_stock_spin.setSuffix(" 個")
        min_stock_layout.addWidget(self.min_stock_spin)
        min_stock_layout.addStretch()
        stock_layout.addRow("最低在庫数:", min_stock_layout)
        
        # 保管場所
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("保管場所を入力してください")
        stock_layout.addRow("保管場所:", self.location_edit)
        
        layout.addWidget(stock_group)
        
        # 詳細情報グループ
        detail_group = QGroupBox("詳細情報")
        detail_group.setFont(QFont("Yu Gothic UI", 10, QFont.Weight.Bold))
        detail_layout = QFormLayout(detail_group)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("商品の詳細情報、注意事項など")
        detail_layout.addRow("備考:", self.notes_edit)
        
        layout.addWidget(detail_group)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton("登録")
        self.save_btn.setStyleSheet("""
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
        
        self.update_btn = QPushButton("更新")
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.update_btn.setVisible(False)
        
        self.delete_btn = QPushButton("削除")
        self.delete_btn.setStyleSheet("""
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
        self.delete_btn.setVisible(False)
        
        self.clear_btn = QPushButton("クリア")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.update_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
    
    def setup_connections(self):
        """シグナル接続"""
        self.save_btn.clicked.connect(self.save_product)
        self.update_btn.clicked.connect(self.update_product)
        self.delete_btn.clicked.connect(self.delete_product)
        self.clear_btn.clicked.connect(self.clear_form)
    
    def validate_form(self) -> bool:
        """フォーム検証"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "入力エラー", "商品名は必須です。")
            self.name_edit.setFocus()
            return False
        
        if self.daily_rate_spin.value() <= 0:
            QMessageBox.warning(self, "入力エラー", "日単価は0より大きい値を入力してください。")
            self.daily_rate_spin.setFocus()
            return False
        
        return True
    
    def save_product(self):
        """商品保存"""
        if not self.validate_form():
            return
        
        try:
            # 商品名重複チェック
            product_name = self.name_edit.text().strip()
            existing_products = db_manager.search(Product, name=product_name)
            if existing_products:
                QMessageBox.warning(self, "入力エラー", 
                                  f"商品名 '{product_name}' は既に使用されています。")
                self.name_edit.setFocus()
                return
            
            product = Product(
                name=product_name,
                model_number=self.model_edit.text().strip(),
                category=self.category_combo.currentText().strip(),
                daily_price=self.daily_rate_spin.value(),
                monthly_price=self.monthly_rate_spin.value(),
                damage_fee=self.damage_rate_spin.value(),
                stock_quantity=self.current_stock_spin.value(),
                min_stock_level=self.min_stock_spin.value(),
                location=self.location_edit.text().strip(),
                notes=self.notes_edit.toPlainText().strip()
            )
            
            saved_product = db_manager.create(product)
            
            # 作成後に商品IDを表示
            self.product_id_edit.setText(str(saved_product.id))
            
            QMessageBox.information(self, "成功", "商品を登録しました。")
            self.product_saved.emit(str(saved_product.id))
            self.clear_form()
            
        except Exception as e:
            logger.error(f"商品保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"保存に失敗しました:\n{str(e)}")
    
    def update_product(self):
        """商品更新"""
        if not self.current_product_id or not self.validate_form():
            return
        
        try:
            product = db_manager.read(Product, id=int(self.current_product_id))[0] if self.current_product_id.isdigit() else None
            if not product:
                QMessageBox.warning(self, "エラー", "商品が見つかりません。")
                return
            
            # データ更新
            product.name = self.name_edit.text().strip()
            product.model_number = self.model_edit.text().strip()
            product.category = self.category_combo.currentText().strip()
            product.daily_price = self.daily_rate_spin.value()
            product.monthly_price = self.monthly_rate_spin.value()
            product.damage_fee = self.damage_rate_spin.value()
            product.stock_quantity = self.current_stock_spin.value()
            product.min_stock_level = self.min_stock_spin.value()
            product.location = self.location_edit.text().strip()
            product.notes = self.notes_edit.toPlainText().strip()
            
            db_manager.update(product)
            
            QMessageBox.information(self, "成功", "商品情報を更新しました。")
            self.product_updated.emit(str(product.id))
            
        except Exception as e:
            logger.error(f"商品更新エラー: {e}")
            QMessageBox.critical(self, "エラー", f"更新に失敗しました:\n{str(e)}")
    
    def delete_product(self):
        """商品削除"""
        if not self.current_product_id:
            return
        
        reply = QMessageBox.question(
            self, "削除確認",
            "選択した商品を削除しますか？\nこの操作は元に戻せません。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                products_to_delete = db_manager.read(Product, id=int(self.current_product_id))
                if products_to_delete:
                    db_manager.delete(products_to_delete[0])
                
                QMessageBox.information(self, "成功", "商品を削除しました。")
                self.product_deleted.emit(self.current_product_id)
                self.clear_form()
                
            except Exception as e:
                logger.error(f"商品削除エラー: {e}")
                QMessageBox.critical(self, "エラー", f"削除に失敗しました:\n{str(e)}")
    
    def clear_form(self):
        """フォームクリア"""
        self.current_product_id = None
        self.product_id_edit.clear()
        self.name_edit.clear()
        self.model_edit.clear()
        self.category_combo.setCurrentIndex(0)
        self.daily_rate_spin.setValue(0)
        self.monthly_rate_spin.setValue(0)
        self.damage_rate_spin.setValue(0)
        self.current_stock_spin.setValue(0)
        self.min_stock_spin.setValue(0)
        self.location_edit.clear()
        self.notes_edit.clear()
        
        # ボタン状態
        self.save_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.delete_btn.setVisible(False)
        
        # 商品ID読み取り専用を維持
        self.product_id_edit.setReadOnly(True)
    
    def load_product(self, product_id: str):
        """商品データ読み込み"""
        try:
            products = db_manager.read(Product, id=int(product_id)) if product_id.isdigit() else []
            if not products:
                QMessageBox.warning(self, "エラー", "商品が見つかりません。")
                return
            
            product = products[0]
            self.current_product_id = str(product.id)
            self.product_id_edit.setText(str(product.id))
            self.name_edit.setText(product.name)
            self.model_edit.setText(product.model_number or "")
            
            # カテゴリ設定
            index = self.category_combo.findText(product.category or "")
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            else:
                self.category_combo.setEditText(product.category or "")
            
            self.daily_rate_spin.setValue(product.daily_price or 0)
            self.monthly_rate_spin.setValue(product.monthly_price or 0)
            self.damage_rate_spin.setValue(product.damage_fee or 0)
            self.current_stock_spin.setValue(product.stock_quantity or 0)
            self.min_stock_spin.setValue(product.min_stock_level or 0)
            self.location_edit.setText(product.location or "")
            self.notes_edit.setPlainText(product.notes or "")
            
            # ボタン状態
            self.save_btn.setVisible(False)
            self.update_btn.setVisible(True)
            self.delete_btn.setVisible(True)
            
            # 商品IDは常に読み取り専用
            self.product_id_edit.setReadOnly(True)
            
        except Exception as e:
            logger.error(f"商品読み込みエラー: {e}")
            QMessageBox.critical(self, "エラー", f"読み込みに失敗しました:\n{str(e)}")


class StockAdjustmentWidget(BaseWidget):
    """在庫調整ウィジェット"""
    
    # シグナル
    stock_adjusted = pyqtSignal(str, int)  # product_id, adjustment
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # 商品選択
        product_group = QGroupBox("商品選択")
        product_layout = QFormLayout(product_group)
        
        self.product_combo = QComboBox()
        self.refresh_products()
        product_layout.addRow("商品:", self.product_combo)
        
        # 現在の在庫表示
        self.current_stock_label = QLabel("0")
        self.current_stock_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        product_layout.addRow("現在庫:", self.current_stock_label)
        
        layout.addWidget(product_group)
        
        # 調整設定
        adjust_group = QGroupBox("在庫調整")
        adjust_layout = QFormLayout(adjust_group)
        
        self.adjustment_spin = QSpinBox()
        self.adjustment_spin.setRange(-9999, 9999)
        self.adjustment_spin.setSuffix(" 個")
        adjust_layout.addRow("調整数量:", self.adjustment_spin)
        
        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("調整理由を入力してください")
        adjust_layout.addRow("調整理由:", self.reason_edit)
        
        layout.addWidget(adjust_group)
        
        # ボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.adjust_btn = QPushButton("在庫調整実行")
        self.adjust_btn.setStyleSheet("""
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
        
        button_layout.addWidget(self.adjust_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
    
    def setup_connections(self):
        """シグナル接続"""
        self.product_combo.currentTextChanged.connect(self.update_current_stock)
        self.adjust_btn.clicked.connect(self.adjust_stock)
    
    def refresh_products(self):
        """商品一覧更新"""
        try:
            self.product_combo.clear()
            products = db_manager.get_all(Product)
            for product in products:
                self.product_combo.addItem(f"{product.name} (ID:{product.id})", product.id)
            
            self.update_current_stock()
            
        except Exception as e:
            logger.error(f"商品一覧取得エラー: {e}")
    
    def update_current_stock(self):
        """現在庫表示更新"""
        product_id = self.product_combo.currentData()
        if product_id:
            try:
                products = db_manager.read(Product, id=product_id)
                if products:
                    self.current_stock_label.setText(str(products[0].stock_quantity or 0))
                else:
                    self.current_stock_label.setText("0")
            except Exception as e:
                logger.error(f"在庫取得エラー: {e}")
                self.current_stock_label.setText("エラー")
        else:
            self.current_stock_label.setText("0")
    
    def adjust_stock(self):
        """在庫調整実行"""
        product_id = self.product_combo.currentData()
        if not product_id:
            QMessageBox.warning(self, "入力エラー", "商品を選択してください。")
            return
        
        adjustment = self.adjustment_spin.value()
        if adjustment == 0:
            QMessageBox.warning(self, "入力エラー", "調整数量を入力してください。")
            return
        
        reason = self.reason_edit.text().strip()
        if not reason:
            QMessageBox.warning(self, "入力エラー", "調整理由を入力してください。")
            return
        
        try:
            products = db_manager.read(Product, id=product_id)
            if not products:
                QMessageBox.warning(self, "エラー", "商品が見つかりません。")
                return
            
            product = products[0]
            new_stock = (product.stock_quantity or 0) + adjustment
            if new_stock < 0:
                QMessageBox.warning(self, "エラー", "在庫数量がマイナスになります。")
                return
            
            # 在庫更新
            product.stock_quantity = new_stock
            db_manager.update(product)
            
            # 調整履歴記録（将来実装）
            
            QMessageBox.information(self, "成功", 
                                  f"在庫調整を実行しました。\n"
                                  f"商品: {product.name}\n"
                                  f"調整: {adjustment:+d}個\n"
                                  f"新在庫: {new_stock}個")
            
            self.stock_adjusted.emit(str(product_id), adjustment)
            self.update_current_stock()
            self.adjustment_spin.setValue(0)
            self.reason_edit.clear()
            
        except Exception as e:
            logger.error(f"在庫調整エラー: {e}")
            QMessageBox.critical(self, "エラー", f"在庫調整に失敗しました:\n{str(e)}")


class ProductListWidget(BaseWidget):
    """商品一覧ウィジェット"""
    
    # シグナル
    product_selected = pyqtSignal(str)  # product_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
        self.refresh_list()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # 検索・フィルタエリア
        filter_layout = QHBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("商品名で検索...")
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("すべてのカテゴリ", "")
        self.category_filter.addItems([
            "プロジェクター", "スクリーン", "音響機器", "照明機器",
            "カメラ", "PC・タブレット", "その他"
        ])
        
        self.low_stock_check = QCheckBox("在庫不足のみ")
        
        self.search_btn = QPushButton("検索")
        self.refresh_btn = QPushButton("更新")
        
        filter_layout.addWidget(QLabel("検索:"))
        filter_layout.addWidget(self.search_edit)
        filter_layout.addWidget(QLabel("カテゴリ:"))
        filter_layout.addWidget(self.category_filter)
        filter_layout.addWidget(self.low_stock_check)
        filter_layout.addWidget(self.search_btn)
        filter_layout.addWidget(self.refresh_btn)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # テーブル
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # ヘッダー設定
        headers = ["商品ID", "商品名", "カテゴリ", "日単価", "月単価", "現在庫", "最低在庫", "在庫状況", "保管場所"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # ヘッダーサイズ調整
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 商品ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 商品名
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # カテゴリ
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 日単価
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 月単価
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 現在庫
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # 最低在庫
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # 在庫状況
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # 保管場所
        
        layout.addWidget(self.table)
    
    def setup_connections(self):
        """シグナル接続"""
        self.search_btn.clicked.connect(self.search_products)
        self.refresh_btn.clicked.connect(self.refresh_list)
        self.search_edit.returnPressed.connect(self.search_products)
        self.category_filter.currentTextChanged.connect(self.search_products)
        self.low_stock_check.toggled.connect(self.search_products)
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)
    
    def refresh_list(self):
        """一覧更新"""
        try:
            products = db_manager.get_all(Product)
            self.populate_table(products)
        except Exception as e:
            logger.error(f"商品一覧取得エラー: {e}")
            QMessageBox.critical(self, "エラー", f"一覧の取得に失敗しました:\n{str(e)}")
    
    def search_products(self):
        """商品検索"""
        try:
            # 検索条件
            search_text = self.search_edit.text().strip()
            category = self.category_filter.currentData() or self.category_filter.currentText()
            if category == "すべてのカテゴリ":
                category = ""
            low_stock_only = self.low_stock_check.isChecked()
            
            # 基本検索
            if search_text:
                products = db_manager.search(Product, name=search_text)
            else:
                products = db_manager.get_all(Product)
            
            # カテゴリフィルタ
            if category:
                products = [p for p in products if p.category == category]
            
            # 在庫不足フィルタ
            if low_stock_only:
                products = [p for p in products 
                          if (p.min_stock_level or 0) > 0 and 
                             (p.stock_quantity or 0) <= (p.min_stock_level or 0)]
            
            self.populate_table(products)
            
        except Exception as e:
            logger.error(f"商品検索エラー: {e}")
            QMessageBox.critical(self, "エラー", f"検索に失敗しました:\n{str(e)}")
    
    def populate_table(self, products: List[Product]):
        """テーブルにデータ設定"""
        self.table.setRowCount(len(products))
        
        for row, product in enumerate(products):
            # データ設定
            self.table.setItem(row, 0, QTableWidgetItem(str(product.id)))
            self.table.setItem(row, 1, QTableWidgetItem(product.name))
            self.table.setItem(row, 2, QTableWidgetItem(product.category or ""))
            self.table.setItem(row, 3, QTableWidgetItem(f"¥{product.daily_price:,.0f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"¥{product.monthly_price:,.0f}" if product.monthly_price else ""))
            self.table.setItem(row, 5, QTableWidgetItem(str(product.stock_quantity or 0)))
            self.table.setItem(row, 6, QTableWidgetItem(str(product.min_stock_level or 0)))
            
            # 在庫状況
            current_stock = product.stock_quantity or 0
            min_stock = product.min_stock_level or 0
            
            if min_stock > 0 and current_stock <= min_stock:
                status = "不足"
                status_color = "#f44336"
            elif min_stock > 0 and current_stock <= min_stock * 1.5:
                status = "注意"
                status_color = "#FF9800"
            else:
                status = "正常"
                status_color = "#4CAF50"
            
            status_item = QTableWidgetItem(status)
            status_item.setBackground(status_color)
            self.table.setItem(row, 7, status_item)
            
            self.table.setItem(row, 8, QTableWidgetItem(product.location or ""))
            
            # 商品IDを行データとして保存
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, str(product.id))
    
    def on_row_double_clicked(self, row: int, column: int):
        """行ダブルクリック"""
        item = self.table.item(row, 0)
        if item:
            product_id = item.data(Qt.ItemDataRole.UserRole)
            self.product_selected.emit(product_id)


class ProductWidget(BaseWidget):
    """商品管理メインウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # フォームヘッダーを追加（エラーハンドリング付き）
        try:
            header_actions = [
                ActionButton(
                    text="新規商品",
                    callback=self.new_product,
                    tooltip="新しい商品を登録します (Ctrl+N)",
                    shortcut="Ctrl+N"
                ),
                ActionButton(
                    text="在庫調整",
                    callback=self.show_stock_adjustment,
                    tooltip="在庫数量を調整します"
                ),
                ActionButton(
                    text="エクスポート",
                    menu=[
                        {"text": "商品リスト(CSV)", "callback": self.export_csv},
                        {"text": "在庫レポート(Excel)", "callback": self.export_stock_report},
                        {"text": "価格表(PDF)", "callback": self.export_price_list}
                    ]
                ),
                ActionButton(
                    text="検索・フィルタ",
                    callback=self.show_search,
                    tooltip="商品の検索とフィルタリング (Ctrl+F)",
                    shortcut="Ctrl+F"
                )
            ]
            
            self.header = FormHeaderWidget(
                title="📦 商品管理",
                actions=header_actions,
                enable_voice_input=True
            )
            self.header.voice_input_received.connect(self.on_voice_input)
            layout.addWidget(self.header)
            
        except Exception as e:
            print(f"FormHeaderWidget作成エラー: {e}")
            # フォールバック：シンプルなタイトルラベルを表示
            title_label = QLabel("📦 商品管理")
            title_label.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
            layout.addWidget(title_label)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumSize(1200, 800)  # タブウィジェットの最小サイズを拡大
        
        # タブウィジェットのスタイル設定
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 12px 30px;
                margin-right: 2px;
                border: 1px solid #c0c0c0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 120px;
                font-size: 14px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background-color: #e0e0e0;
            }
        """)
        
        # フォームタブ
        self.form_widget = ProductFormWidget()
        self.form_widget.setMinimumWidth(950)  # フォームの最小幅を拡大
        self.tab_widget.addTab(self.form_widget, "📝 商品登録・編集")
        
        # 一覧タブ
        self.list_widget = ProductListWidget()
        self.list_widget.setMinimumWidth(1100)  # 一覧の最小幅を拡大
        self.tab_widget.addTab(self.list_widget, "📋 商品一覧")
        
        # 在庫調整タブ
        self.stock_widget = StockAdjustmentWidget()
        self.stock_widget.setMinimumWidth(700)  # 在庫調整の最小幅を拡大
        self.tab_widget.addTab(self.stock_widget, "📦 在庫調整")
        
        layout.addWidget(self.tab_widget)
    
    def setup_connections(self):
        """シグナル接続"""
        # フォームからのシグナル
        self.form_widget.product_saved.connect(self.on_product_changed)
        self.form_widget.product_updated.connect(self.on_product_changed)
        self.form_widget.product_deleted.connect(self.on_product_changed)
        
        # 一覧からのシグナル
        self.list_widget.product_selected.connect(self.on_product_selected)
        
        # 在庫調整からのシグナル
        self.stock_widget.stock_adjusted.connect(self.on_stock_adjusted)
    
    def on_product_changed(self, product_id: str):
        """商品変更時"""
        self.list_widget.refresh_list()
        self.stock_widget.refresh_products()
    
    def on_product_selected(self, product_id: str):
        """商品選択時"""
        # 編集タブに切り替え
        self.tab_widget.setCurrentIndex(0)
        # データ読み込み
        self.form_widget.load_product(product_id)
    
    def on_stock_adjusted(self, product_id: str, adjustment: int):
        """在庫調整時"""
        self.list_widget.refresh_list()
    
    def new_product(self):
        """新規商品作成"""
        self.tab_widget.setCurrentIndex(0)  # フォームタブに切り替え
        self.form_widget.clear_form()
    
    def show_stock_adjustment(self):
        """在庫調整画面表示"""
        self.tab_widget.setCurrentIndex(2)  # 在庫調整タブに切り替え
    
    def export_csv(self):
        """商品リストをCSV形式でエクスポート"""
        # TODO: CSV エクスポート機能を実装
        print("商品リスト CSV エクスポート機能（未実装）")
    
    def export_stock_report(self):
        """在庫レポートをExcel形式でエクスポート"""
        # TODO: Excel エクスポート機能を実装
        print("在庫レポート Excel エクスポート機能（未実装）")
    
    def export_price_list(self):
        """価格表をPDF形式でエクスポート"""
        # TODO: PDF エクスポート機能を実装
        print("価格表 PDF エクスポート機能（未実装）")
    
    def show_search(self):
        """検索画面表示"""
        self.tab_widget.setCurrentIndex(1)  # 一覧タブに切り替え
        self.list_widget.search_edit.setFocus()
    
    def on_voice_input(self, text: str):
        """音声入力処理"""
        print(f"音声入力を受信: {text}")
        # TODO: 音声コマンドの解析と実行を実装
        # 例: "新規商品"と言ったら new_product() を実行
        if "新規" in text or "新し" in text:
            self.new_product()
        elif "在庫" in text:
            self.show_stock_adjustment()
        elif "検索" in text or "探し" in text:
            self.show_search()
        elif "エクスポート" in text or "出力" in text:
            self.export_csv()  # デフォルトはCSV