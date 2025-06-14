#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v3.0 - 請求書管理モジュール
PyQt6ベースの請求書作成・管理機能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QComboBox, QCheckBox, QMessageBox, QHeaderView,
    QSplitter, QGroupBox, QLabel, QDateEdit, QSpinBox,
    QDoubleSpinBox, QRadioButton, QButtonGroup, QFrame,
    QScrollArea, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QDateTime
from PyQt6.QtGui import QFont, QPixmap, QIcon
from typing import Optional, List, Dict, Any, Tuple
import logging
from datetime import datetime, timedelta
import json

from core.database import Invoice, InvoiceDetail, Customer, Product, Loan, db_manager
from ui.components.base_widget import BaseWidget

logger = logging.getLogger(__name__)


class InvoiceFormWidget(BaseWidget):
    """請求書作成フォームウィジェット"""
    
    # シグナル
    invoice_saved = pyqtSignal(str)  # invoice_id
    invoice_updated = pyqtSignal(str)
    invoice_deleted = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_invoice_id: Optional[str] = None
        self.invoice_details: List[Dict[str, Any]] = []
        self.tax_rate = 0.10  # 消費税率
        self.setup_ui()
        self.setup_connections()
        self.refresh_customers()
    
    def setup_ui(self):
        """UI設定"""
        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(16)
        
        # 基本情報グループ
        basic_group = QGroupBox("請求書基本情報")
        basic_group.setFont(QFont("Yu Gothic UI", 10, QFont.Weight.Bold))
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(12)
        
        # 請求書ID（自動生成）
        self.invoice_id_label = QLabel("（自動生成）")
        self.invoice_id_label.setStyleSheet("color: #666; font-style: italic;")
        basic_layout.addRow("請求書ID:", self.invoice_id_label)
        
        # 取引先選択
        customer_layout = QHBoxLayout()
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(200)
        self.refresh_customer_btn = QPushButton("更新")
        self.refresh_customer_btn.setMaximumWidth(60)
        customer_layout.addWidget(self.customer_combo)
        customer_layout.addWidget(self.refresh_customer_btn)
        customer_layout.addStretch()
        basic_layout.addRow("取引先 *:", customer_layout)
        
        # 請求期間
        period_layout = QHBoxLayout()
        self.period_from_edit = QDateEdit()
        self.period_from_edit.setDate(QDate.currentDate().addDays(-30))
        self.period_from_edit.setCalendarPopup(True)
        self.period_to_edit = QDateEdit()
        self.period_to_edit.setDate(QDate.currentDate())
        self.period_to_edit.setCalendarPopup(True)
        period_layout.addWidget(self.period_from_edit)
        period_layout.addWidget(QLabel("～"))
        period_layout.addWidget(self.period_to_edit)
        period_layout.addStretch()
        basic_layout.addRow("請求期間 *:", period_layout)
        
        layout.addWidget(basic_group)
        
        # オプション設定グループ
        option_group = QGroupBox("オプション設定")
        option_group.setFont(QFont("Yu Gothic UI", 10, QFont.Weight.Bold))
        option_layout = QVBoxLayout(option_group)
        
        # チェックボックス
        checkbox_layout = QHBoxLayout()
        self.initial_fee_check = QCheckBox("初回料金を含む")
        self.damage_fee_check = QCheckBox("破損料金を含む")
        checkbox_layout.addWidget(self.initial_fee_check)
        checkbox_layout.addWidget(self.damage_fee_check)
        checkbox_layout.addStretch()
        option_layout.addLayout(checkbox_layout)
        
        # 税区分
        tax_layout = QHBoxLayout()
        self.tax_group = QButtonGroup()
        self.tax_included_radio = QRadioButton("税込み（内税）")
        self.tax_excluded_radio = QRadioButton("税抜き（外税）")
        self.tax_excluded_radio.setChecked(True)  # デフォルト
        self.tax_group.addButton(self.tax_included_radio, 0)
        self.tax_group.addButton(self.tax_excluded_radio, 1)
        tax_layout.addWidget(self.tax_included_radio)
        tax_layout.addWidget(self.tax_excluded_radio)
        tax_layout.addStretch()
        option_layout.addLayout(tax_layout)
        
        layout.addWidget(option_group)
        
        # 明細生成ボタン
        generate_layout = QHBoxLayout()
        generate_layout.addStretch()
        self.generate_btn = QPushButton("明細を自動生成")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        generate_layout.addWidget(self.generate_btn)
        layout.addLayout(generate_layout)
        
        # 明細表示グループ
        detail_group = QGroupBox("請求明細")
        detail_group.setFont(QFont("Yu Gothic UI", 10, QFont.Weight.Bold))
        detail_layout = QVBoxLayout(detail_group)
        
        # 明細テーブル
        self.detail_table = QTableWidget()
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        headers = ["商品名", "数量", "単価", "金額", "貸出日", "返却日", "日数"]
        self.detail_table.setColumnCount(len(headers))
        self.detail_table.setHorizontalHeaderLabels(headers)
        self.detail_table.setMaximumHeight(200)
        
        # ヘッダーサイズ調整
        header = self.detail_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 商品名
        for i in range(1, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        detail_layout.addWidget(self.detail_table)
        
        # 明細操作ボタン
        detail_btn_layout = QHBoxLayout()
        self.add_detail_btn = QPushButton("明細追加")
        self.edit_detail_btn = QPushButton("明細編集")
        self.delete_detail_btn = QPushButton("明細削除")
        detail_btn_layout.addWidget(self.add_detail_btn)
        detail_btn_layout.addWidget(self.edit_detail_btn)
        detail_btn_layout.addWidget(self.delete_detail_btn)
        detail_btn_layout.addStretch()
        detail_layout.addLayout(detail_btn_layout)
        
        layout.addWidget(detail_group)
        
        # 金額計算グループ
        calc_group = QGroupBox("金額計算")
        calc_group.setFont(QFont("Yu Gothic UI", 10, QFont.Weight.Bold))
        calc_layout = QFormLayout(calc_group)
        
        # 小計
        self.subtotal_label = QLabel("¥0")
        self.subtotal_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        calc_layout.addRow("小計:", self.subtotal_label)
        
        # 初回料金
        initial_fee_layout = QHBoxLayout()
        self.initial_fee_spin = QDoubleSpinBox()
        self.initial_fee_spin.setRange(0, 999999)
        self.initial_fee_spin.setDecimals(0)
        self.initial_fee_spin.setSuffix(" 円")
        initial_fee_layout.addWidget(self.initial_fee_spin)
        initial_fee_layout.addStretch()
        calc_layout.addRow("初回料金:", initial_fee_layout)
        
        # 破損料金
        damage_fee_layout = QHBoxLayout()
        self.damage_fee_spin = QDoubleSpinBox()
        self.damage_fee_spin.setRange(0, 999999)
        self.damage_fee_spin.setDecimals(0)
        self.damage_fee_spin.setSuffix(" 円")
        damage_fee_layout.addWidget(self.damage_fee_spin)
        damage_fee_layout.addStretch()
        calc_layout.addRow("破損料金:", damage_fee_layout)
        
        # 税額
        self.tax_label = QLabel("¥0")
        self.tax_label.setStyleSheet("font-weight: bold; color: #666;")
        calc_layout.addRow("税額:", self.tax_label)
        
        # 合計
        self.total_label = QLabel("¥0")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #d32f2f;")
        calc_layout.addRow("合計:", self.total_label)
        
        layout.addWidget(calc_group)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.setStyleSheet("""
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
        
        self.print_btn = QPushButton("印刷")
        self.pdf_btn = QPushButton("PDF出力")
        self.clear_btn = QPushButton("クリア")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.update_btn)
        button_layout.addWidget(self.print_btn)
        button_layout.addWidget(self.pdf_btn)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        scroll.setWidget(content_widget)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
    
    def setup_connections(self):
        """シグナル接続"""
        self.generate_btn.clicked.connect(self.generate_details)
        self.save_btn.clicked.connect(self.save_invoice)
        self.update_btn.clicked.connect(self.update_invoice)
        self.clear_btn.clicked.connect(self.clear_form)
        self.refresh_customer_btn.clicked.connect(self.refresh_customers)
        
        # 金額計算連動
        self.initial_fee_spin.valueChanged.connect(self.calculate_total)
        self.damage_fee_spin.valueChanged.connect(self.calculate_total)
        self.tax_included_radio.toggled.connect(self.calculate_total)
        self.tax_excluded_radio.toggled.connect(self.calculate_total)
    
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
    
    def generate_details(self):
        """明細自動生成"""
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, "入力エラー", "取引先を選択してください。")
            return
        
        period_from = self.period_from_edit.date().toPython()
        period_to = self.period_to_edit.date().toPython()
        
        if period_from > period_to:
            QMessageBox.warning(self, "入力エラー", "期間の開始日が終了日より後になっています。")
            return
        
        try:
            # 期間内の貸出データを取得
            loans = db_manager.get_loans_for_period(customer_id, period_from, period_to)
            
            if not loans:
                QMessageBox.information(self, "情報", "指定期間内に貸出データがありません。")
                return
            
            # 明細データ作成
            self.invoice_details = []
            for loan in loans:
                # 商品情報取得
                product = db_manager.get_by_id(Product, loan.product_id)
                if not product:
                    continue
                
                # 貸出日数計算
                loan_date = loan.loan_date
                return_date = loan.return_date or period_to
                days = (return_date - loan_date).days + 1
                
                # 金額計算
                unit_price = product.daily_rate
                amount = unit_price * loan.quantity * days
                
                detail = {
                    'product_name': product.name,
                    'quantity': loan.quantity,
                    'unit_price': unit_price,
                    'amount': amount,
                    'loan_date': loan_date,
                    'return_date': return_date,
                    'days': days,
                    'loan_id': loan.id,
                    'product_id': loan.product_id
                }
                
                self.invoice_details.append(detail)
            
            # テーブル更新
            self.update_detail_table()
            
            # 金額計算
            self.calculate_total()
            
            QMessageBox.information(self, "成功", f"{len(self.invoice_details)}件の明細を生成しました。")
            
        except Exception as e:
            logger.error(f"明細生成エラー: {e}")
            QMessageBox.critical(self, "エラー", f"明細生成に失敗しました:\n{str(e)}")
    
    def update_detail_table(self):
        """明細テーブル更新"""
        self.detail_table.setRowCount(len(self.invoice_details))
        
        for row, detail in enumerate(self.invoice_details):
            self.detail_table.setItem(row, 0, QTableWidgetItem(detail['product_name']))
            self.detail_table.setItem(row, 1, QTableWidgetItem(str(detail['quantity'])))
            self.detail_table.setItem(row, 2, QTableWidgetItem(f"¥{detail['unit_price']:,.0f}"))
            self.detail_table.setItem(row, 3, QTableWidgetItem(f"¥{detail['amount']:,.0f}"))
            self.detail_table.setItem(row, 4, QTableWidgetItem(detail['loan_date'].strftime("%Y/%m/%d")))
            self.detail_table.setItem(row, 5, QTableWidgetItem(detail['return_date'].strftime("%Y/%m/%d")))
            self.detail_table.setItem(row, 6, QTableWidgetItem(str(detail['days'])))
    
    def calculate_total(self):
        """合計金額計算"""
        # 小計
        subtotal = sum(detail['amount'] for detail in self.invoice_details)
        self.subtotal_label.setText(f"¥{subtotal:,.0f}")
        
        # 追加料金
        initial_fee = self.initial_fee_spin.value()
        damage_fee = self.damage_fee_spin.value()
        
        # 課税対象額
        taxable_amount = subtotal + initial_fee + damage_fee
        
        # 税額計算
        if self.tax_included_radio.isChecked():
            # 内税
            tax_amount = taxable_amount * self.tax_rate / (1 + self.tax_rate)
            total_amount = taxable_amount
        else:
            # 外税
            tax_amount = taxable_amount * self.tax_rate
            total_amount = taxable_amount + tax_amount
        
        self.tax_label.setText(f"¥{tax_amount:,.0f}")
        self.total_label.setText(f"¥{total_amount:,.0f}")
    
    def validate_form(self) -> bool:
        """フォーム検証"""
        if not self.customer_combo.currentData():
            QMessageBox.warning(self, "入力エラー", "取引先を選択してください。")
            return False
        
        if not self.invoice_details:
            QMessageBox.warning(self, "入力エラー", "請求明細がありません。明細を生成してください。")
            return False
        
        return True
    
    def save_invoice(self):
        """請求書保存"""
        if not self.validate_form():
            return
        
        try:
            # 請求書ID生成
            invoice_id = self.generate_invoice_id()
            
            # 請求書作成
            invoice = Invoice(
                invoice_id=invoice_id,
                customer_id=self.customer_combo.currentData(),
                period_from=self.period_from_edit.date().toPython(),
                period_to=self.period_to_edit.date().toPython(),
                subtotal=sum(detail['amount'] for detail in self.invoice_details),
                initial_fee=self.initial_fee_spin.value(),
                damage_fee=self.damage_fee_spin.value(),
                tax_included=self.tax_included_radio.isChecked(),
                notes="",
                status="作成済"
            )
            
            saved_invoice = db_manager.create(invoice)
            
            # 明細保存
            for detail in self.invoice_details:
                invoice_detail = InvoiceDetail(
                    invoice_id=invoice_id,
                    product_id=detail['product_id'],
                    product_name=detail['product_name'],
                    quantity=detail['quantity'],
                    unit_price=detail['unit_price'],
                    amount=detail['amount'],
                    loan_date=detail['loan_date'],
                    return_date=detail['return_date']
                )
                db_manager.create(invoice_detail)
            
            QMessageBox.information(self, "成功", f"請求書を保存しました。\n請求書ID: {invoice_id}")
            self.invoice_saved.emit(invoice_id)
            self.clear_form()
            
        except Exception as e:
            logger.error(f"請求書保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"保存に失敗しました:\n{str(e)}")
    
    def update_invoice(self):
        """請求書更新"""
        if not self.current_invoice_id:
            QMessageBox.warning(self, "エラー", "更新する請求書が選択されていません。")
            return
        
        if not self.validate_form():
            return
        
        try:
            # 既存の請求書を検索
            invoices = db_manager.read(Invoice, invoice_id=self.current_invoice_id)
            if not invoices:
                QMessageBox.warning(self, "エラー", "更新対象の請求書が見つかりません。")
                return
            
            invoice = invoices[0]
            
            # 請求書情報を更新
            updated_data = {
                'customer_id': self.customer_combo.currentData(),
                'period_from': self.period_from_edit.date().toPython(),
                'period_to': self.period_to_edit.date().toPython(),
                'subtotal': sum(detail['amount'] for detail in self.invoice_details),
                'initial_fee': self.initial_fee_spin.value(),
                'damage_fee': self.damage_fee_spin.value(),
                'tax_included': self.tax_included_radio.isChecked(),
                'status': "更新済"
            }
            
            db_manager.update(invoice, **updated_data)
            
            # 既存の明細を削除
            existing_details = db_manager.read(InvoiceDetail, invoice_id=self.current_invoice_id)
            for detail in existing_details:
                db_manager.delete(detail)
            
            # 新しい明細を保存
            for detail in self.invoice_details:
                invoice_detail = InvoiceDetail(
                    invoice_id=self.current_invoice_id,
                    product_id=detail['product_id'],
                    product_name=detail['product_name'],
                    quantity=detail['quantity'],
                    unit_price=detail['unit_price'],
                    amount=detail['amount'],
                    loan_date=detail['loan_date'],
                    return_date=detail['return_date']
                )
                db_manager.create(invoice_detail)
            
            QMessageBox.information(self, "成功", f"請求書を更新しました。\n請求書ID: {self.current_invoice_id}")
            self.invoice_updated.emit(self.current_invoice_id)
            
        except Exception as e:
            logger.error(f"請求書更新エラー: {e}")
            QMessageBox.critical(self, "エラー", f"更新に失敗しました:\n{str(e)}")
    
    def generate_invoice_id(self) -> str:
        """請求書ID生成"""
        today = datetime.now()
        prefix = f"INV{today.strftime('%Y%m%d')}"
        
        # 同日の請求書数を確認
        existing_count = len(db_manager.search(Invoice, invoice_id=f"{prefix}%"))
        
        return f"{prefix}{existing_count + 1:03d}"
    
    def clear_form(self):
        """フォームクリア"""
        self.current_invoice_id = None
        self.customer_combo.setCurrentIndex(0)
        self.period_from_edit.setDate(QDate.currentDate().addDays(-30))
        self.period_to_edit.setDate(QDate.currentDate())
        self.initial_fee_check.setChecked(False)
        self.damage_fee_check.setChecked(False)
        self.tax_excluded_radio.setChecked(True)
        self.initial_fee_spin.setValue(0)
        self.damage_fee_spin.setValue(0)
        self.invoice_details = []
        self.update_detail_table()
        self.calculate_total()
        
        # ボタン状態
        self.save_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.invoice_id_label.setText("（自動生成）")


class InvoiceListWidget(BaseWidget):
    """請求書一覧ウィジェット"""
    
    # シグナル
    invoice_selected = pyqtSignal(str)  # invoice_id
    
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
        self.search_edit.setPlaceholderText("請求書ID、取引先名で検索...")
        
        self.status_filter = QComboBox()
        self.status_filter.addItem("すべてのステータス", "")
        self.status_filter.addItem("作成済", "作成済")
        self.status_filter.addItem("送付済", "送付済")
        self.status_filter.addItem("入金済", "入金済")
        
        self.search_btn = QPushButton("検索")
        self.refresh_btn = QPushButton("更新")
        
        filter_layout.addWidget(QLabel("検索:"))
        filter_layout.addWidget(self.search_edit)
        filter_layout.addWidget(QLabel("ステータス:"))
        filter_layout.addWidget(self.status_filter)
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
        headers = ["請求書ID", "取引先", "請求期間", "小計", "税額", "合計", "ステータス", "作成日"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # ヘッダーサイズ調整
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 請求書ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 取引先
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 請求期間
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 小計
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 税額
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 合計
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # ステータス
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # 作成日
        
        layout.addWidget(self.table)
    
    def setup_connections(self):
        """シグナル接続"""
        self.search_btn.clicked.connect(self.search_invoices)
        self.refresh_btn.clicked.connect(self.refresh_list)
        self.search_edit.returnPressed.connect(self.search_invoices)
        self.status_filter.currentTextChanged.connect(self.search_invoices)
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)
    
    def refresh_list(self):
        """一覧更新"""
        try:
            invoices = db_manager.get_all(Invoice)
            self.populate_table(invoices)
        except Exception as e:
            logger.error(f"請求書一覧取得エラー: {e}")
            QMessageBox.critical(self, "エラー", f"一覧の取得に失敗しました:\n{str(e)}")
    
    def search_invoices(self):
        """請求書検索"""
        search_text = self.search_edit.text().strip()
        status = self.status_filter.currentData()
        
        try:
            # 基本検索
            if search_text:
                invoices = db_manager.search(Invoice, invoice_id=search_text)
                # 取引先名でも検索
                customers = db_manager.search(Customer, name=search_text)
                for customer in customers:
                    customer_invoices = db_manager.search(Invoice, customer_id=customer.id)
                    invoices.extend(customer_invoices)
                # 重複除去
                invoices = list({inv.invoice_id: inv for inv in invoices}.values())
            else:
                invoices = db_manager.get_all(Invoice)
            
            # ステータスフィルタ
            if status:
                invoices = [inv for inv in invoices if inv.status == status]
            
            self.populate_table(invoices)
            
        except Exception as e:
            logger.error(f"請求書検索エラー: {e}")
            QMessageBox.critical(self, "エラー", f"検索に失敗しました:\n{str(e)}")
    
    def populate_table(self, invoices: List[Invoice]):
        """テーブルにデータ設定"""
        self.table.setRowCount(len(invoices))
        
        for row, invoice in enumerate(invoices):
            # 取引先名取得
            customer = db_manager.get_by_id(Customer, invoice.customer_id)
            customer_name = customer.name if customer else "不明"
            
            # 合計金額計算
            total_amount = (invoice.subtotal or 0) + (invoice.initial_fee or 0) + (invoice.damage_fee or 0)
            if invoice.tax_included:
                tax_amount = total_amount * 0.1 / 1.1
            else:
                tax_amount = total_amount * 0.1
                total_amount += tax_amount
            
            # データ設定
            self.table.setItem(row, 0, QTableWidgetItem(invoice.invoice_id))
            self.table.setItem(row, 1, QTableWidgetItem(customer_name))
            
            period_text = f"{invoice.period_from.strftime('%Y/%m/%d')} ～ {invoice.period_to.strftime('%Y/%m/%d')}"
            self.table.setItem(row, 2, QTableWidgetItem(period_text))
            
            self.table.setItem(row, 3, QTableWidgetItem(f"¥{invoice.subtotal:,.0f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"¥{tax_amount:,.0f}"))
            self.table.setItem(row, 5, QTableWidgetItem(f"¥{total_amount:,.0f}"))
            self.table.setItem(row, 6, QTableWidgetItem(invoice.status or "作成済"))
            
            created_date = invoice.created_at.strftime("%Y/%m/%d") if invoice.created_at else ""
            self.table.setItem(row, 7, QTableWidgetItem(created_date))
            
            # 請求書IDを行データとして保存
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, invoice.invoice_id)
    
    def on_row_double_clicked(self, row: int, column: int):
        """行ダブルクリック"""
        item = self.table.item(row, 0)
        if item:
            invoice_id = item.data(Qt.ItemDataRole.UserRole)
            self.invoice_selected.emit(invoice_id)


class InvoiceWidget(BaseWidget):
    """請求書管理メインウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumSize(1300, 850)  # タブウィジェットの最小サイズを設定
        
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
        
        # 作成タブ
        self.form_widget = InvoiceFormWidget()
        self.form_widget.setMinimumWidth(1100)  # フォームの最小幅を設定
        self.tab_widget.addTab(self.form_widget, "💼 請求書作成")
        
        # 一覧タブ
        self.list_widget = InvoiceListWidget()
        self.list_widget.setMinimumWidth(1200)  # 一覧の最小幅を設定
        self.tab_widget.addTab(self.list_widget, "📊 請求書一覧")
        
        layout.addWidget(self.tab_widget)
    
    def setup_connections(self):
        """シグナル接続"""
        # フォームからのシグナル
        self.form_widget.invoice_saved.connect(self.on_invoice_saved)
        
        # 一覧からのシグナル
        self.list_widget.invoice_selected.connect(self.on_invoice_selected)
    
    def on_invoice_saved(self, invoice_id: str):
        """請求書保存時"""
        self.list_widget.refresh_list()
    
    def on_invoice_selected(self, invoice_id: str):
        """請求書選択時"""
        # 詳細表示や編集機能は将来実装
        QMessageBox.information(self, "情報", f"請求書 {invoice_id} が選択されました。\n編集機能は将来のバージョンで実装予定です。")