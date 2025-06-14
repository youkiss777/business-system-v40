#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v3.0 - 取引先管理モジュール
PyQt6ベースの取引先管理機能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QComboBox, QCheckBox, QMessageBox, QHeaderView,
    QSplitter, QGroupBox, QLabel, QDateEdit, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QFont
from typing import Optional, List, Dict, Any
import logging

from core.database import Customer, db_manager
from ui.components.base_widget import BaseWidget
from ui.components.form_header import FormHeaderWidget, ActionButton

logger = logging.getLogger(__name__)


class CustomerFormWidget(BaseWidget):
    """取引先入力フォームウィジェット"""
    
    # シグナル
    customer_saved = pyqtSignal(int)  # customer_id
    customer_updated = pyqtSignal(int)
    customer_deleted = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_customer_id: Optional[int] = None
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # フォームグループ
        form_group = QGroupBox("取引先情報")
        form_group.setFont(QFont("Yu Gothic UI", 12, QFont.Weight.Bold))
        form_group.setMinimumWidth(900)  # フォームグループの最小幅を大幅拡大
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(15)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # 基本情報
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("取引先名を入力してください")
        self.name_edit.setMinimumHeight(40)  # 入力フィールドの高さを拡大
        self.name_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        form_layout.addRow("取引先名 *:", self.name_edit)
        
        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("住所を入力してください")
        self.address_edit.setMinimumHeight(40)
        self.address_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        form_layout.addRow("住所:", self.address_edit)
        
        self.postal_code_edit = QLineEdit()
        self.postal_code_edit.setPlaceholderText("123-4567")
        self.postal_code_edit.setMinimumHeight(40)
        self.postal_code_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        form_layout.addRow("郵便番号:", self.postal_code_edit)
        
        # 連絡先情報
        contact_layout = QHBoxLayout()
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("03-1234-5678")
        self.phone_edit.setMinimumHeight(40)
        self.phone_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        self.fax_edit = QLineEdit()
        self.fax_edit.setPlaceholderText("03-1234-5679")
        self.fax_edit.setMinimumHeight(40)
        self.fax_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        contact_layout.addWidget(self.phone_edit)
        contact_layout.addWidget(QLabel("FAX:"))
        contact_layout.addWidget(self.fax_edit)
        form_layout.addRow("電話番号:", contact_layout)
        
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("example@company.com")
        self.email_edit.setMinimumHeight(40)
        self.email_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        form_layout.addRow("Email:", self.email_edit)
        
        self.contact_person_edit = QLineEdit()
        self.contact_person_edit.setPlaceholderText("担当者名")
        self.contact_person_edit.setMinimumHeight(40)
        self.contact_person_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        form_layout.addRow("担当者:", self.contact_person_edit)
        
        # 請求設定
        billing_layout = QHBoxLayout()
        self.closing_day_spin = QSpinBox()
        self.closing_day_spin.setRange(1, 31)
        self.closing_day_spin.setValue(31)
        self.payment_terms_spin = QSpinBox()
        self.payment_terms_spin.setRange(0, 180)
        self.payment_terms_spin.setValue(30)
        self.payment_terms_spin.setSuffix("日")
        billing_layout.addWidget(self.closing_day_spin)
        billing_layout.addWidget(QLabel("日締め"))
        billing_layout.addWidget(self.payment_terms_spin)
        form_layout.addRow("請求条件:", billing_layout)
        
        # オプション設定
        self.initial_fee_check = QCheckBox("初回料金を適用")
        form_layout.addRow("オプション:", self.initial_fee_check)
        
        # 備考
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        self.notes_edit.setMinimumHeight(80)
        self.notes_edit.setPlaceholderText("備考を入力してください")
        self.notes_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px;")
        form_layout.addRow("備考:", self.notes_edit)
        
        layout.addWidget(form_group)
        
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
        self.save_btn.clicked.connect(self.save_customer)
        self.update_btn.clicked.connect(self.update_customer)
        self.delete_btn.clicked.connect(self.delete_customer)
        self.clear_btn.clicked.connect(self.clear_form)
    
    def validate_form(self) -> bool:
        """フォーム検証"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "入力エラー", "取引先名は必須です。")
            self.name_edit.setFocus()
            return False
        
        # Email形式チェック
        email = self.email_edit.text().strip()
        if email and '@' not in email:
            QMessageBox.warning(self, "入力エラー", "正しいEmail形式で入力してください。")
            self.email_edit.setFocus()
            return False
        
        return True
    
    def save_customer(self):
        """取引先保存"""
        if not self.validate_form():
            return
        
        try:
            # 取引先名重複チェック
            customer_name = self.name_edit.text().strip()
            existing_customers = db_manager.search(Customer, name=customer_name)
            if existing_customers:
                QMessageBox.warning(self, "入力エラー", 
                                  f"取引先名 '{customer_name}' は既に使用されています。")
                self.name_edit.setFocus()
                return
            
            customer = Customer(
                name=customer_name,
                address=self.address_edit.text().strip(),
                postal_code=self.postal_code_edit.text().strip(),
                phone=self.phone_edit.text().strip(),
                fax=self.fax_edit.text().strip(),
                email=self.email_edit.text().strip(),
                contact_person=self.contact_person_edit.text().strip(),
                closing_day=self.closing_day_spin.value(),
                payment_terms=self.payment_terms_spin.value(),
                initial_fee_flag=self.initial_fee_check.isChecked(),
                notes=self.notes_edit.toPlainText().strip()
            )
            
            saved_customer = db_manager.create(customer)
            
            QMessageBox.information(self, "成功", "取引先を登録しました。")
            self.customer_saved.emit(saved_customer.id)
            self.clear_form()
            
        except Exception as e:
            logger.error(f"取引先保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"保存に失敗しました:\n{str(e)}")
    
    def update_customer(self):
        """取引先更新"""
        if not self.current_customer_id or not self.validate_form():
            return
        
        try:
            customer = db_manager.get_by_id(Customer, self.current_customer_id)
            if not customer:
                QMessageBox.warning(self, "エラー", "取引先が見つかりません。")
                return
            
            # データ更新
            customer.name = self.name_edit.text().strip()
            customer.address = self.address_edit.text().strip()
            customer.postal_code = self.postal_code_edit.text().strip()
            customer.phone = self.phone_edit.text().strip()
            customer.fax = self.fax_edit.text().strip()
            customer.email = self.email_edit.text().strip()
            customer.contact_person = self.contact_person_edit.text().strip()
            customer.closing_day = self.closing_day_spin.value()
            customer.payment_terms = self.payment_terms_spin.value()
            customer.initial_fee_flag = self.initial_fee_check.isChecked()
            customer.notes = self.notes_edit.toPlainText().strip()
            
            db_manager.update(customer)
            
            QMessageBox.information(self, "成功", "取引先情報を更新しました。")
            self.customer_updated.emit(customer.id)
            
        except Exception as e:
            logger.error(f"取引先更新エラー: {e}")
            QMessageBox.critical(self, "エラー", f"更新に失敗しました:\n{str(e)}")
    
    def delete_customer(self):
        """取引先削除"""
        if not self.current_customer_id:
            return
        
        reply = QMessageBox.question(
            self, "削除確認",
            "選択した取引先を削除しますか？\nこの操作は元に戻せません。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db_manager.delete_by_id(Customer, self.current_customer_id)
                
                QMessageBox.information(self, "成功", "取引先を削除しました。")
                self.customer_deleted.emit(self.current_customer_id)
                self.clear_form()
                
            except Exception as e:
                logger.error(f"取引先削除エラー: {e}")
                QMessageBox.critical(self, "エラー", f"削除に失敗しました:\n{str(e)}")
    
    def clear_form(self):
        """フォームクリア"""
        self.current_customer_id = None
        self.name_edit.clear()
        self.address_edit.clear()
        self.postal_code_edit.clear()
        self.phone_edit.clear()
        self.fax_edit.clear()
        self.email_edit.clear()
        self.contact_person_edit.clear()
        self.closing_day_spin.setValue(31)
        self.payment_terms_spin.setValue(30)
        self.initial_fee_check.setChecked(False)
        self.notes_edit.clear()
        
        # ボタン状態
        self.save_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.delete_btn.setVisible(False)
    
    def load_customer(self, customer_id: int):
        """取引先データ読み込み"""
        try:
            customer = db_manager.get_by_id(Customer, customer_id)
            if not customer:
                QMessageBox.warning(self, "エラー", "取引先が見つかりません。")
                return
            
            self.current_customer_id = customer.id
            self.name_edit.setText(customer.name)
            self.address_edit.setText(customer.address or "")
            self.postal_code_edit.setText(customer.postal_code or "")
            self.phone_edit.setText(customer.phone or "")
            self.fax_edit.setText(customer.fax or "")
            self.email_edit.setText(customer.email or "")
            self.contact_person_edit.setText(customer.contact_person or "")
            self.closing_day_spin.setValue(customer.closing_day or 31)
            self.payment_terms_spin.setValue(customer.payment_terms or 30)
            self.initial_fee_check.setChecked(customer.initial_fee_flag or False)
            self.notes_edit.setPlainText(customer.notes or "")
            
            # ボタン状態
            self.save_btn.setVisible(False)
            self.update_btn.setVisible(True)
            self.delete_btn.setVisible(True)
            
        except Exception as e:
            logger.error(f"取引先読み込みエラー: {e}")
            QMessageBox.critical(self, "エラー", f"読み込みに失敗しました:\n{str(e)}")


class CustomerListWidget(BaseWidget):
    """取引先一覧ウィジェット"""
    
    # シグナル
    customer_selected = pyqtSignal(int)  # customer_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
        self.refresh_list()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # 検索エリア
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("取引先名で検索...")
        self.search_btn = QPushButton("検索")
        self.refresh_btn = QPushButton("更新")
        
        search_layout.addWidget(QLabel("検索:"))
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.refresh_btn)
        search_layout.addStretch()
        
        layout.addLayout(search_layout)
        
        # テーブル
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # ヘッダー設定
        headers = ["ID", "取引先名", "住所", "電話番号", "Email", "担当者", "請求条件", "登録日"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # ヘッダーサイズ調整
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 取引先名
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # 住所
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 電話番号
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Email
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 担当者
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # 請求条件
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # 登録日
        
        layout.addWidget(self.table)
    
    def setup_connections(self):
        """シグナル接続"""
        self.search_btn.clicked.connect(self.search_customers)
        self.refresh_btn.clicked.connect(self.refresh_list)
        self.search_edit.returnPressed.connect(self.search_customers)
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)
    
    def refresh_list(self):
        """一覧更新"""
        try:
            customers = db_manager.get_all(Customer)
            self.populate_table(customers)
        except Exception as e:
            logger.error(f"取引先一覧取得エラー: {e}")
            QMessageBox.critical(self, "エラー", f"一覧の取得に失敗しました:\n{str(e)}")
    
    def search_customers(self):
        """取引先検索"""
        search_text = self.search_edit.text().strip()
        if not search_text:
            self.refresh_list()
            return
        
        try:
            customers = db_manager.search(Customer, name=search_text)
            self.populate_table(customers)
        except Exception as e:
            logger.error(f"取引先検索エラー: {e}")
            QMessageBox.critical(self, "エラー", f"検索に失敗しました:\n{str(e)}")
    
    def populate_table(self, customers: List[Customer]):
        """テーブルにデータ設定"""
        self.table.setRowCount(len(customers))
        
        for row, customer in enumerate(customers):
            # データ設定
            self.table.setItem(row, 0, QTableWidgetItem(str(customer.id)))
            self.table.setItem(row, 1, QTableWidgetItem(customer.name))
            self.table.setItem(row, 2, QTableWidgetItem(customer.address or ""))
            self.table.setItem(row, 3, QTableWidgetItem(customer.phone or ""))
            self.table.setItem(row, 4, QTableWidgetItem(customer.email or ""))
            self.table.setItem(row, 5, QTableWidgetItem(customer.contact_person or ""))
            
            # 請求条件
            billing_info = f"{customer.closing_day or 31}日締め / {customer.payment_terms or 30}日払い"
            self.table.setItem(row, 6, QTableWidgetItem(billing_info))
            
            # 登録日
            register_date = customer.created_at.strftime("%Y/%m/%d") if customer.created_at else ""
            self.table.setItem(row, 7, QTableWidgetItem(register_date))
            
            # IDを行データとして保存
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, customer.id)
    
    def on_row_double_clicked(self, row: int, column: int):
        """行ダブルクリック"""
        item = self.table.item(row, 0)
        if item:
            customer_id = item.data(Qt.ItemDataRole.UserRole)
            self.customer_selected.emit(customer_id)


class CustomerWidget(BaseWidget):
    """取引先管理メインウィジェット"""
    
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
                    text="新規取引先",
                    callback=self.new_customer,
                    tooltip="新しい取引先を登録します (Ctrl+N)",
                    shortcut="Ctrl+N"
                ),
                ActionButton(
                    text="エクスポート",
                    menu=[
                        {"text": "CSVエクスポート", "callback": self.export_csv},
                        {"text": "Excelエクスポート", "callback": self.export_excel},
                        {"text": "PDFエクスポート", "callback": self.export_pdf}
                    ]
                ),
                ActionButton(
                    text="インポート",
                    callback=self.import_data,
                    tooltip="取引先データをインポート"
                ),
                ActionButton(
                    text="検索",
                    callback=self.show_search,
                    tooltip="高度な検索 (Ctrl+F)",
                    shortcut="Ctrl+F"
                )
            ]
            
            self.header = FormHeaderWidget(
                title="👥 取引先管理",
                actions=header_actions,
                enable_voice_input=True
            )
            self.header.voice_input_received.connect(self.on_voice_input)
            layout.addWidget(self.header)
            
        except Exception as e:
            print(f"FormHeaderWidget作成エラー: {e}")
            # フォールバック：シンプルなタイトルラベルを表示
            title_label = QLabel("👥 取引先管理")
            title_label.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
            layout.addWidget(title_label)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumSize(1300, 850)  # タブウィジェットの最小サイズを更に拡大
        
        # タブウィジェットのスタイル設定
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 12px 35px;
                margin-right: 2px;
                border: 1px solid #c0c0c0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 140px;
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
        self.form_widget = CustomerFormWidget()
        self.form_widget.setMinimumWidth(1050)  # フォームの最小幅を更に拡大
        self.tab_widget.addTab(self.form_widget, "📝 取引先登録・編集")
        
        # 一覧タブ
        self.list_widget = CustomerListWidget()
        self.list_widget.setMinimumWidth(1200)  # 一覧の最小幅を更に拡大
        self.tab_widget.addTab(self.list_widget, "📋 取引先一覧")
        
        layout.addWidget(self.tab_widget)
    
    def setup_connections(self):
        """シグナル接続"""
        # フォームからのシグナル
        self.form_widget.customer_saved.connect(self.on_customer_saved)
        self.form_widget.customer_updated.connect(self.on_customer_updated)
        self.form_widget.customer_deleted.connect(self.on_customer_deleted)
        
        # 一覧からのシグナル
        self.list_widget.customer_selected.connect(self.on_customer_selected)
    
    def on_customer_saved(self, customer_id: int):
        """取引先保存時"""
        self.list_widget.refresh_list()
    
    def on_customer_updated(self, customer_id: int):
        """取引先更新時"""
        self.list_widget.refresh_list()
    
    def on_customer_deleted(self, customer_id: int):
        """取引先削除時"""
        self.list_widget.refresh_list()
    
    def on_customer_selected(self, customer_id: int):
        """取引先選択時"""
        # 編集タブに切り替え
        self.tab_widget.setCurrentIndex(0)
        # データ読み込み
        self.form_widget.load_customer(customer_id)
    
    def new_customer(self):
        """新規取引先作成"""
        self.tab_widget.setCurrentIndex(0)  # フォームタブに切り替え
        self.form_widget.clear_form()
    
    def export_csv(self):
        """CSV形式でエクスポート"""
        # TODO: CSV エクスポート機能を実装
        print("CSV エクスポート機能（未実装）")
    
    def export_excel(self):
        """Excel形式でエクスポート"""
        # TODO: Excel エクスポート機能を実装
        print("Excel エクスポート機能（未実装）")
    
    def export_pdf(self):
        """PDF形式でエクスポート"""
        # TODO: PDF エクスポート機能を実装
        print("PDF エクスポート機能（未実装）")
    
    def import_data(self):
        """データインポート"""
        # TODO: データインポート機能を実装
        print("データインポート機能（未実装）")
    
    def show_search(self):
        """検索画面表示"""
        self.tab_widget.setCurrentIndex(1)  # 一覧タブに切り替え
        self.list_widget.search_edit.setFocus()
    
    def on_voice_input(self, text: str):
        """音声入力処理"""
        print(f"音声入力を受信: {text}")
        # TODO: 音声コマンドの解析と実行を実装
        # 例: "新規取引先"と言ったら new_customer() を実行
        if "新規" in text or "新し" in text:
            self.new_customer()
        elif "検索" in text or "探し" in text:
            self.show_search()
        elif "エクスポート" in text or "出力" in text:
            self.export_csv()  # デフォルトはCSV