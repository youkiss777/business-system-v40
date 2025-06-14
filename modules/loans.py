#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v3.0 - 貸出管理モジュール
PyQt6ベースの貸出登録・返却・履歴管理機能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QComboBox, QCheckBox, QMessageBox, QHeaderView,
    QSplitter, QGroupBox, QLabel, QDateEdit, QSpinBox,
    QDoubleSpinBox, QFrame, QScrollArea, QTreeWidget, QTreeWidgetItem,
    QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QDateTime, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon
from typing import Optional, List, Dict, Any, Tuple
import logging
from datetime import datetime, timedelta

from core.database import Loan, Customer, Product, db_manager
from ui.components.base_widget import BaseWidget

logger = logging.getLogger(__name__)


class LoanFormWidget(BaseWidget):
    """貸出登録フォームウィジェット"""
    
    # シグナル
    loan_saved = pyqtSignal(int)  # loan_id
    loan_updated = pyqtSignal(int)
    loan_returned = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_loan_id: Optional[int] = None
        self.loan_items: List[Dict[str, Any]] = []
        self.setup_ui()
        self.setup_connections()
        self.refresh_customers()
        self.refresh_products()
    
    def setup_ui(self):
        """UI設定"""
        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(16)
        
        # 基本情報グループ
        basic_group = QGroupBox("貸出基本情報")
        basic_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(15)
        
        # 取引先選択
        customer_layout = QHBoxLayout()
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(250)
        self.customer_combo.setStyleSheet("font-size: 14px; padding: 8px;")
        self.refresh_customer_btn = QPushButton("更新")
        self.refresh_customer_btn.setMaximumWidth(80)
        customer_layout.addWidget(self.customer_combo)
        customer_layout.addWidget(self.refresh_customer_btn)
        customer_layout.addStretch()
        basic_layout.addRow(QLabel("取引先 *:"), customer_layout)
        
        # 貸出日
        self.loan_date_edit = QDateEdit()
        self.loan_date_edit.setDate(QDate.currentDate())
        self.loan_date_edit.setCalendarPopup(True)
        self.loan_date_edit.setStyleSheet("font-size: 14px; padding: 8px;")
        basic_layout.addRow(QLabel("貸出日 *:"), self.loan_date_edit)
        
        # 返却予定日
        self.return_date_edit = QDateEdit()
        self.return_date_edit.setDate(QDate.currentDate().addDays(7))
        self.return_date_edit.setCalendarPopup(True)
        self.return_date_edit.setStyleSheet("font-size: 14px; padding: 8px;")
        basic_layout.addRow(QLabel("返却予定日:"), self.return_date_edit)
        
        # 備考
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("特記事項があれば入力してください")
        self.notes_edit.setStyleSheet("font-size: 14px; padding: 8px;")
        basic_layout.addRow(QLabel("備考:"), self.notes_edit)
        
        layout.addWidget(basic_group)
        
        # 商品追加エリア
        product_group = QGroupBox("商品選択・追加")
        product_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        product_layout = QVBoxLayout(product_group)
        
        # 商品選択行
        product_select_layout = QHBoxLayout()
        
        self.product_combo = QComboBox()
        self.product_combo.setMinimumWidth(200)
        self.product_combo.setStyleSheet("font-size: 14px; padding: 8px;")
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 999)
        self.quantity_spin.setValue(1)
        self.quantity_spin.setStyleSheet("font-size: 14px; padding: 8px;")
        
        self.unit_price_spin = QDoubleSpinBox()
        self.unit_price_spin.setRange(0, 999999)
        self.unit_price_spin.setDecimals(0)
        self.unit_price_spin.setSuffix(" 円")
        self.unit_price_spin.setStyleSheet("font-size: 14px; padding: 8px;")
        
        self.add_item_btn = QPushButton("商品を追加")
        self.add_item_btn.setStyleSheet("""
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
        
        product_select_layout.addWidget(QLabel("商品:"))
        product_select_layout.addWidget(self.product_combo)
        product_select_layout.addWidget(QLabel("数量:"))
        product_select_layout.addWidget(self.quantity_spin)
        product_select_layout.addWidget(QLabel("単価:"))
        product_select_layout.addWidget(self.unit_price_spin)
        product_select_layout.addWidget(self.add_item_btn)
        product_select_layout.addStretch()
        
        product_layout.addLayout(product_select_layout)
        
        # 選択商品一覧テーブル
        self.items_table = QTableWidget()
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        headers = ["商品名", "数量", "日単価", "月単価", "小計", "在庫状況", "操作"]
        self.items_table.setColumnCount(len(headers))
        self.items_table.setHorizontalHeaderLabels(headers)
        self.items_table.setMaximumHeight(200)
        
        # ヘッダーサイズ調整
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 商品名
        for i in range(1, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        product_layout.addWidget(self.items_table)
        
        # 合計金額表示
        total_layout = QHBoxLayout()
        total_layout.addStretch()
        self.total_label = QLabel("合計: ¥0")
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #d32f2f;")
        total_layout.addWidget(self.total_label)
        product_layout.addLayout(total_layout)
        
        layout.addWidget(product_group)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton("貸出登録")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        self.clear_btn = QPushButton("クリア")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        scroll.setWidget(content_widget)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
    
    def setup_connections(self):
        """シグナル接続"""
        self.add_item_btn.clicked.connect(self.add_loan_item)
        self.save_btn.clicked.connect(self.save_loan)
        self.clear_btn.clicked.connect(self.clear_form)
        self.refresh_customer_btn.clicked.connect(self.refresh_customers)
        
        # 商品選択時に単価自動設定
        self.product_combo.currentTextChanged.connect(self.update_unit_price)
    
    def refresh_customers(self):
        """取引先一覧更新"""
        try:
            self.customer_combo.clear()
            self.customer_combo.addItem("取引先を選択してください", None)
            
            customers = db_manager.get_all(Customer)
            for customer in customers:
                self.customer_combo.addItem(customer.name, customer.id)
                
        except Exception as e:
            logger.error(f"取引先一覧取得エラー: {e}")
    
    def refresh_products(self):
        """商品一覧更新"""
        try:
            self.product_combo.clear()
            self.product_combo.addItem("商品を選択してください", None)
            
            products = db_manager.get_all(Product)
            for product in products:
                display_text = f"{product.name} (在庫: {product.current_stock or 0})"
                self.product_combo.addItem(display_text, product.product_id)
                
        except Exception as e:
            logger.error(f"商品一覧取得エラー: {e}")
    
    def update_unit_price(self):
        """単価自動設定"""
        product_id = self.product_combo.currentData()
        if product_id:
            try:
                product = db_manager.get_by_id(Product, product_id)
                if product:
                    self.unit_price_spin.setValue(product.daily_rate or 0)
            except Exception as e:
                logger.error(f"単価取得エラー: {e}")
    
    def add_loan_item(self):
        """貸出商品追加"""
        product_id = self.product_combo.currentData()
        if not product_id:
            QMessageBox.warning(self, "入力エラー", "商品を選択してください。")
            return
        
        quantity = self.quantity_spin.value()
        unit_price = self.unit_price_spin.value()
        
        try:
            product = db_manager.get_by_id(Product, product_id)
            if not product:
                QMessageBox.warning(self, "エラー", "商品情報が見つかりません。")
                return
            
            # 在庫チェック
            current_stock = product.current_stock or 0
            if current_stock < quantity:
                reply = QMessageBox.question(
                    self, "在庫不足",
                    f"在庫が不足しています。\n"
                    f"要求数量: {quantity}、現在庫: {current_stock}\n"
                    f"それでも追加しますか？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # 重複チェック
            for item in self.loan_items:
                if item['product_id'] == product_id:
                    item['quantity'] += quantity
                    item['subtotal'] = item['quantity'] * item['unit_price']
                    self.update_items_table()
                    self.calculate_total()
                    return
            
            # 新規追加
            item = {
                'product_id': product_id,
                'product_name': product.name,
                'quantity': quantity,
                'unit_price': unit_price,
                'monthly_rate': product.monthly_rate or 0,
                'subtotal': quantity * unit_price,
                'current_stock': current_stock,
                'stock_status': "不足" if current_stock < quantity else "正常"
            }
            
            self.loan_items.append(item)
            self.update_items_table()
            self.calculate_total()
            
            # フォームリセット
            self.product_combo.setCurrentIndex(0)
            self.quantity_spin.setValue(1)
            self.unit_price_spin.setValue(0)
            
        except Exception as e:
            logger.error(f"商品追加エラー: {e}")
            QMessageBox.critical(self, "エラー", f"商品追加に失敗しました:\n{str(e)}")
    
    def update_items_table(self):
        """商品一覧テーブル更新"""
        self.items_table.setRowCount(len(self.loan_items))
        
        for row, item in enumerate(self.loan_items):
            self.items_table.setItem(row, 0, QTableWidgetItem(item['product_name']))
            self.items_table.setItem(row, 1, QTableWidgetItem(str(item['quantity'])))
            self.items_table.setItem(row, 2, QTableWidgetItem(f"¥{item['unit_price']:,.0f}"))
            self.items_table.setItem(row, 3, QTableWidgetItem(f"¥{item['monthly_rate']:,.0f}"))
            self.items_table.setItem(row, 4, QTableWidgetItem(f"¥{item['subtotal']:,.0f}"))
            
            # 在庫状況
            status_item = QTableWidgetItem(item['stock_status'])
            if item['stock_status'] == "不足":
                status_item.setBackground(Qt.GlobalColor.red)
            else:
                status_item.setBackground(Qt.GlobalColor.lightGreen)
            self.items_table.setItem(row, 5, status_item)
            
            # 削除ボタン
            delete_btn = QPushButton("削除")
            delete_btn.clicked.connect(lambda checked, r=row: self.remove_item(r))
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            self.items_table.setCellWidget(row, 6, delete_btn)
    
    def remove_item(self, row: int):
        """商品削除"""
        if 0 <= row < len(self.loan_items):
            del self.loan_items[row]
            self.update_items_table()
            self.calculate_total()
    
    def calculate_total(self):
        """合計金額計算"""
        total = sum(item['subtotal'] for item in self.loan_items)
        self.total_label.setText(f"合計: ¥{total:,.0f}")
    
    def validate_form(self) -> bool:
        """フォーム検証"""
        if not self.customer_combo.currentData():
            QMessageBox.warning(self, "入力エラー", "取引先を選択してください。")
            return False
        
        if not self.loan_items:
            QMessageBox.warning(self, "入力エラー", "貸出商品を追加してください。")
            return False
        
        return True
    
    def save_loan(self):
        """貸出保存"""
        if not self.validate_form():
            return
        
        try:
            customer_id = self.customer_combo.currentData()
            loan_date = self.loan_date_edit.date().toPython()
            return_date = self.return_date_edit.date().toPython()
            notes = self.notes_edit.toPlainText().strip()
            
            # 各商品ごとに貸出レコード作成
            saved_loans = []
            
            for item in self.loan_items:
                loan = Loan(
                    customer_id=customer_id,
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    unit_price=item['unit_price'],
                    total_amount=item['subtotal'],
                    loan_date=loan_date,
                    expected_return_date=return_date,
                    notes=notes,
                    status="貸出中"
                )
                
                saved_loan = db_manager.create(loan)
                saved_loans.append(saved_loan)
                
                # 在庫更新
                product = db_manager.get_by_id(Product, item['product_id'])
                if product:
                    product.current_stock = (product.current_stock or 0) - item['quantity']
                    db_manager.update(product)
            
            QMessageBox.information(self, "成功", 
                                  f"{len(saved_loans)}件の貸出を登録しました。\n"
                                  f"取引先: {self.customer_combo.currentText()}\n"
                                  f"貸出日: {loan_date.strftime('%Y/%m/%d')}")
            
            # シグナル発行
            for loan in saved_loans:
                self.loan_saved.emit(loan.id)
            
            self.clear_form()
            
        except Exception as e:
            logger.error(f"貸出保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"貸出登録に失敗しました:\n{str(e)}")
    
    def clear_form(self):
        """フォームクリア"""
        self.customer_combo.setCurrentIndex(0)
        self.loan_date_edit.setDate(QDate.currentDate())
        self.return_date_edit.setDate(QDate.currentDate().addDays(7))
        self.notes_edit.clear()
        self.product_combo.setCurrentIndex(0)
        self.quantity_spin.setValue(1)
        self.unit_price_spin.setValue(0)
        self.loan_items.clear()
        self.update_items_table()
        self.calculate_total()


class LoanListWidget(BaseWidget):
    """貸出一覧ウィジェット"""
    
    # シグナル
    loan_selected = pyqtSignal(int)  # loan_id
    loan_returned = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
        self.refresh_list()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # フィルタエリア
        filter_layout = QHBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("取引先名、商品名で検索...")
        self.search_edit.setStyleSheet("font-size: 14px; padding: 8px;")
        
        self.status_filter = QComboBox()
        self.status_filter.addItem("すべてのステータス", "")
        self.status_filter.addItem("貸出中", "貸出中")
        self.status_filter.addItem("返却済", "返却済")
        self.status_filter.addItem("延滞", "延滞")
        self.status_filter.setStyleSheet("font-size: 14px; padding: 8px;")
        
        self.search_btn = QPushButton("検索")
        self.refresh_btn = QPushButton("更新")
        self.return_btn = QPushButton("返却処理")
        self.return_btn.setStyleSheet("""
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
        
        filter_layout.addWidget(QLabel("検索:"))
        filter_layout.addWidget(self.search_edit)
        filter_layout.addWidget(QLabel("ステータス:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addWidget(self.search_btn)
        filter_layout.addWidget(self.refresh_btn)
        filter_layout.addWidget(self.return_btn)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # テーブル
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # ヘッダー設定
        headers = ["ID", "取引先", "商品名", "数量", "単価", "金額", "貸出日", "返却予定", "ステータス", "備考"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # ヘッダーサイズ調整
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 取引先
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # 商品名
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 数量
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 単価
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 金額
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # 貸出日
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # 返却予定
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # ステータス
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)  # 備考
        
        layout.addWidget(self.table)
    
    def setup_connections(self):
        """シグナル接続"""
        self.search_btn.clicked.connect(self.search_loans)
        self.refresh_btn.clicked.connect(self.refresh_list)
        self.return_btn.clicked.connect(self.return_loan)
        self.search_edit.returnPressed.connect(self.search_loans)
        self.status_filter.currentTextChanged.connect(self.search_loans)
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)
    
    def refresh_list(self):
        """一覧更新"""
        try:
            loans = db_manager.get_all(Loan)
            self.populate_table(loans)
        except Exception as e:
            logger.error(f"貸出一覧取得エラー: {e}")
            QMessageBox.critical(self, "エラー", f"一覧の取得に失敗しました:\n{str(e)}")
    
    def search_loans(self):
        """貸出検索"""
        search_text = self.search_edit.text().strip()
        status = self.status_filter.currentData()
        
        try:
            # 基本検索
            loans = db_manager.get_all(Loan)
            
            # テキスト検索
            if search_text:
                filtered_loans = []
                for loan in loans:
                    # 取引先名検索
                    customer = db_manager.get_by_id(Customer, loan.customer_id)
                    customer_name = customer.name if customer else ""
                    
                    # 商品名検索
                    product = db_manager.get_by_id(Product, loan.product_id)
                    product_name = product.name if product else ""
                    
                    if (search_text.lower() in customer_name.lower() or 
                        search_text.lower() in product_name.lower()):
                        filtered_loans.append(loan)
                
                loans = filtered_loans
            
            # ステータスフィルタ
            if status:
                loans = [loan for loan in loans if loan.status == status]
            
            self.populate_table(loans)
            
        except Exception as e:
            logger.error(f"貸出検索エラー: {e}")
            QMessageBox.critical(self, "エラー", f"検索に失敗しました:\n{str(e)}")
    
    def populate_table(self, loans: List[Loan]):
        """テーブルにデータ設定"""
        self.table.setRowCount(len(loans))
        
        today = datetime.now().date()
        
        for row, loan in enumerate(loans):
            # 取引先名・商品名取得
            customer = db_manager.get_by_id(Customer, loan.customer_id)
            customer_name = customer.name if customer else "不明"
            
            product = db_manager.get_by_id(Product, loan.product_id)
            product_name = product.name if product else "不明"
            
            # データ設定
            self.table.setItem(row, 0, QTableWidgetItem(str(loan.id)))
            self.table.setItem(row, 1, QTableWidgetItem(customer_name))
            self.table.setItem(row, 2, QTableWidgetItem(product_name))
            self.table.setItem(row, 3, QTableWidgetItem(str(loan.quantity)))
            self.table.setItem(row, 4, QTableWidgetItem(f"¥{loan.unit_price:,.0f}"))
            self.table.setItem(row, 5, QTableWidgetItem(f"¥{loan.total_amount:,.0f}"))
            self.table.setItem(row, 6, QTableWidgetItem(loan.loan_date.strftime("%Y/%m/%d")))
            
            expected_return = loan.expected_return_date.strftime("%Y/%m/%d") if loan.expected_return_date else ""
            self.table.setItem(row, 7, QTableWidgetItem(expected_return))
            
            # ステータス（延滞チェック付き）
            status = loan.status
            if (status == "貸出中" and loan.expected_return_date and 
                loan.expected_return_date < today):
                status = "延滞"
            
            status_item = QTableWidgetItem(status)
            if status == "延滞":
                status_item.setBackground(Qt.GlobalColor.red)
                status_item.setForeground(Qt.GlobalColor.white)
            elif status == "貸出中":
                status_item.setBackground(Qt.GlobalColor.yellow)
            elif status == "返却済":
                status_item.setBackground(Qt.GlobalColor.lightGreen)
            
            self.table.setItem(row, 8, status_item)
            self.table.setItem(row, 9, QTableWidgetItem(loan.notes or ""))
            
            # 貸出IDを行データとして保存
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, loan.id)
    
    def return_loan(self):
        """返却処理"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "選択エラー", "返却する貸出を選択してください。")
            return
        
        loan_id = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        
        try:
            loan = db_manager.get_by_id(Loan, loan_id)
            if not loan:
                QMessageBox.warning(self, "エラー", "貸出情報が見つかりません。")
                return
            
            if loan.status == "返却済":
                QMessageBox.information(self, "情報", "この貸出は既に返却済みです。")
                return
            
            reply = QMessageBox.question(
                self, "返却確認",
                f"以下の貸出を返却しますか？\n\n"
                f"商品: {self.table.item(current_row, 2).text()}\n"
                f"数量: {self.table.item(current_row, 3).text()}\n"
                f"取引先: {self.table.item(current_row, 1).text()}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 返却処理
                loan.status = "返却済"
                loan.actual_return_date = datetime.now().date()
                db_manager.update(loan)
                
                # 在庫復元
                product = db_manager.get_by_id(Product, loan.product_id)
                if product:
                    product.current_stock = (product.current_stock or 0) + loan.quantity
                    db_manager.update(product)
                
                QMessageBox.information(self, "成功", "返却処理が完了しました。")
                self.loan_returned.emit(loan_id)
                self.refresh_list()
            
        except Exception as e:
            logger.error(f"返却処理エラー: {e}")
            QMessageBox.critical(self, "エラー", f"返却処理に失敗しました:\n{str(e)}")
    
    def on_row_double_clicked(self, row: int, column: int):
        """行ダブルクリック"""
        item = self.table.item(row, 0)
        if item:
            loan_id = item.data(Qt.ItemDataRole.UserRole)
            self.loan_selected.emit(loan_id)


class LoanWidget(BaseWidget):
    """貸出管理メインウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumSize(1250, 800)  # タブウィジェットの最小サイズを設定
        
        # タブウィジェットのスタイル設定
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 12px 40px;
                margin-right: 2px;
                border: 1px solid #c0c0c0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 150px;
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
        
        # 貸出登録タブ
        self.form_widget = LoanFormWidget()
        self.form_widget.setMinimumWidth(1000)  # フォームの最小幅を設定
        self.tab_widget.addTab(self.form_widget, "🛠 貸出登録")
        
        # 一覧・返却タブ
        self.list_widget = LoanListWidget()
        self.list_widget.setMinimumWidth(1150)  # 一覧の最小幅を設定
        self.tab_widget.addTab(self.list_widget, "📋 貸出一覧・返却")
        
        layout.addWidget(self.tab_widget)
    
    def setup_connections(self):
        """シグナル接続"""
        # フォームからのシグナル
        self.form_widget.loan_saved.connect(self.on_loan_saved)
        
        # 一覧からのシグナル
        self.list_widget.loan_returned.connect(self.on_loan_returned)
        self.list_widget.loan_selected.connect(self.on_loan_selected)
    
    def on_loan_saved(self, loan_id: int):
        """貸出保存時"""
        self.list_widget.refresh_list()
    
    def on_loan_returned(self, loan_id: int):
        """返却時"""
        self.list_widget.refresh_list()
    
    def on_loan_selected(self, loan_id: int):
        """貸出選択時"""
        # 詳細表示機能は将来実装
        pass