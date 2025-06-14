#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v3.0 - 売上分析・レポートモジュール
PyQt6ベースの売上集計・グラフ表示・レポート生成機能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QComboBox, QCheckBox, QMessageBox, QHeaderView,
    QSplitter, QGroupBox, QLabel, QDateEdit, QSpinBox,
    QDoubleSpinBox, QFrame, QScrollArea, QTreeWidget, QTreeWidgetItem,
    QProgressBar, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QDateTime, QTimer, QThread
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPainter, QPen
from typing import Optional, List, Dict, Any, Tuple
import logging
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FigureCanvas = QWidget
    Figure = object

import pandas as pd
import numpy as np

from core.database import Loan, Customer, Product, Invoice, db_manager
from ui.components.base_widget import BaseWidget

logger = logging.getLogger(__name__)


class SalesChart(FigureCanvas if MATPLOTLIB_AVAILABLE else QWidget):
    """売上グラフウィジェット"""
    
    def __init__(self, parent=None):
        if MATPLOTLIB_AVAILABLE:
            self.figure = Figure(figsize=(12, 8), dpi=100)
            super().__init__(self.figure)
            self.setParent(parent)
            
            # 日本語フォント設定
            plt.rcParams['font.family'] = ['DejaVu Sans', 'Yu Gothic', 'Hiragino Sans', 'Noto Sans CJK JP']
            self.figure.patch.set_facecolor('white')
        else:
            super().__init__(parent)
            layout = QVBoxLayout(self)
            error_label = QLabel("グラフ機能を使用するには matplotlib をインストールしてください。\n\npip install matplotlib")
            error_label.setStyleSheet("color: #666; font-size: 14px; text-align: center;")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def plot_monthly_sales(self, data: List[Dict[str, Any]]):
        """月別売上グラフ"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        if not data:
            ax.text(0.5, 0.5, 'データがありません', ha='center', va='center', transform=ax.transAxes)
            self.draw()
            return
        
        # データ準備
        months = [item['month'] for item in data]
        sales = [item['total_sales'] for item in data]
        
        # 棒グラフ
        bars = ax.bar(months, sales, color='#2196F3', alpha=0.7, edgecolor='#1976D2')
        
        # グラフ設定
        ax.set_title('月別売上推移', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('月', fontsize=12)
        ax.set_ylabel('売上金額 (円)', fontsize=12)
        
        # Y軸フォーマット
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'¥{x:,.0f}'))
        
        # 値ラベル表示
        for bar, value in zip(bars, sales):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + max(sales)*0.01,
                   f'¥{value:,.0f}', ha='center', va='bottom', fontsize=10)
        
        # グリッド
        ax.grid(True, alpha=0.3, axis='y')
        
        # レイアウト調整
        self.figure.tight_layout()
        self.draw()
    
    def plot_product_ranking(self, data: List[Dict[str, Any]]):
        """商品別売上ランキング"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        if not data:
            ax.text(0.5, 0.5, 'データがありません', ha='center', va='center', transform=ax.transAxes)
            self.draw()
            return
        
        # データ準備（上位10件）
        top_data = data[:10]
        products = [item['product_name'] for item in top_data]
        sales = [item['total_sales'] for item in top_data]
        
        # 横棒グラフ
        bars = ax.barh(products, sales, color='#FF9800', alpha=0.7, edgecolor='#F57C00')
        
        # グラフ設定
        ax.set_title('商品別売上ランキング（上位10位）', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('売上金額 (円)', fontsize=12)
        
        # X軸フォーマット
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'¥{x:,.0f}'))
        
        # 値ラベル表示
        for bar, value in zip(bars, sales):
            width = bar.get_width()
            ax.text(width + max(sales)*0.01, bar.get_y() + bar.get_height()/2.,
                   f'¥{value:,.0f}', ha='left', va='center', fontsize=10)
        
        # グリッド
        ax.grid(True, alpha=0.3, axis='x')
        
        # レイアウト調整
        self.figure.tight_layout()
        self.draw()
    
    def plot_customer_analysis(self, data: List[Dict[str, Any]]):
        """取引先別分析"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        self.figure.clear()
        
        # 2つのサブプロット
        ax1 = self.figure.add_subplot(121)
        ax2 = self.figure.add_subplot(122)
        
        if not data:
            ax1.text(0.5, 0.5, 'データがありません', ha='center', va='center', transform=ax1.transAxes)
            ax2.text(0.5, 0.5, 'データがありません', ha='center', va='center', transform=ax2.transAxes)
            self.draw()
            return
        
        # データ準備
        customers = [item['customer_name'] for item in data[:5]]  # 上位5社
        sales = [item['total_sales'] for item in data[:5]]
        counts = [item['loan_count'] for item in data[:5]]
        
        # 売上金額（左）
        bars1 = ax1.bar(customers, sales, color='#4CAF50', alpha=0.7)
        ax1.set_title('取引先別売上金額（上位5社）', fontsize=12, fontweight='bold')
        ax1.set_ylabel('売上金額 (円)')
        ax1.tick_params(axis='x', rotation=45)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'¥{x:,.0f}'))
        
        # 利用回数（右）
        bars2 = ax2.bar(customers, counts, color='#9C27B0', alpha=0.7)
        ax2.set_title('取引先別利用回数（上位5社）', fontsize=12, fontweight='bold')
        ax2.set_ylabel('利用回数')
        ax2.tick_params(axis='x', rotation=45)
        
        # レイアウト調整
        self.figure.tight_layout()
        self.draw()


class AnalyticsWidget(BaseWidget):
    """売上分析メインウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
        self.refresh_data()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # 期間選択エリア
        period_group = QGroupBox("分析期間設定")
        period_group.setFont(QFont("Yu Gothic UI", 10, QFont.Weight.Bold))
        period_layout = QHBoxLayout(period_group)
        
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "過去12ヶ月", "過去6ヶ月", "過去3ヶ月", "今年", "昨年", "カスタム期間"
        ])
        self.period_combo.setStyleSheet("font-size: 14px; padding: 8px;")
        
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addMonths(-12))
        self.date_from.setCalendarPopup(True)
        self.date_from.setStyleSheet("font-size: 14px; padding: 8px;")
        
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setStyleSheet("font-size: 14px; padding: 8px;")
        
        self.analyze_btn = QPushButton("分析実行")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        period_layout.addWidget(QLabel("期間:"))
        period_layout.addWidget(self.period_combo)
        period_layout.addWidget(QLabel("開始:"))
        period_layout.addWidget(self.date_from)
        period_layout.addWidget(QLabel("終了:"))
        period_layout.addWidget(self.date_to)
        period_layout.addWidget(self.analyze_btn)
        period_layout.addStretch()
        
        layout.addWidget(period_group)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumSize(1200, 750)  # タブウィジェットの最小サイズを設定
        
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
                min-width: 130px;
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
        
        # 概要タブ
        self.setup_summary_tab()
        
        # 月別売上タブ
        self.setup_monthly_tab()
        
        # 商品分析タブ
        self.setup_product_tab()
        
        # 取引先分析タブ
        self.setup_customer_tab()
        
        # レポート出力タブ
        self.setup_report_tab()
        
        layout.addWidget(self.tab_widget)
    
    def setup_summary_tab(self):
        """概要タブ設定"""
        summary_widget = QWidget()
        layout = QVBoxLayout(summary_widget)
        
        # KPI表示エリア
        kpi_frame = QFrame()
        kpi_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        kpi_layout = QHBoxLayout(kpi_frame)
        
        # KPI項目
        self.kpi_labels = {}
        kpi_items = [
            ("total_sales", "総売上", "¥0", "#2196F3"),
            ("total_loans", "総貸出数", "0件", "#4CAF50"),
            ("avg_per_loan", "平均単価", "¥0", "#FF9800"),
            ("active_customers", "利用客数", "0社", "#9C27B0")
        ]
        
        for key, title, default_value, color in kpi_items:
            kpi_widget = QWidget()
            kpi_widget_layout = QVBoxLayout(kpi_widget)
            kpi_widget_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            title_label = QLabel(title)
            title_label.setStyleSheet(f"font-size: 12px; color: {color}; font-weight: bold;")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            value_label = QLabel(default_value)
            value_label.setStyleSheet(f"font-size: 24px; color: {color}; font-weight: bold;")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            kpi_widget_layout.addWidget(title_label)
            kpi_widget_layout.addWidget(value_label)
            
            self.kpi_labels[key] = value_label
            kpi_layout.addWidget(kpi_widget)
        
        layout.addWidget(kpi_frame)
        
        # 簡易グラフエリア
        self.summary_chart = SalesChart()
        layout.addWidget(self.summary_chart)
        
        self.tab_widget.addTab(summary_widget, "📊 概要")
    
    def setup_monthly_tab(self):
        """月別売上タブ設定"""
        monthly_widget = QWidget()
        layout = QVBoxLayout(monthly_widget)
        
        # グラフ
        self.monthly_chart = SalesChart()
        layout.addWidget(self.monthly_chart)
        
        # データテーブル
        self.monthly_table = QTableWidget()
        self.monthly_table.setMaximumHeight(200)
        headers = ["月", "売上金額", "貸出件数", "平均単価", "前月比"]
        self.monthly_table.setColumnCount(len(headers))
        self.monthly_table.setHorizontalHeaderLabels(headers)
        layout.addWidget(self.monthly_table)
        
        self.tab_widget.addTab(monthly_widget, "📅 月別売上")
    
    def setup_product_tab(self):
        """商品分析タブ設定"""
        product_widget = QWidget()
        layout = QVBoxLayout(product_widget)
        
        # グラフ
        self.product_chart = SalesChart()
        layout.addWidget(self.product_chart)
        
        # データテーブル
        self.product_table = QTableWidget()
        self.product_table.setMaximumHeight(250)
        headers = ["商品名", "売上金額", "貸出回数", "平均単価", "シェア率"]
        self.product_table.setColumnCount(len(headers))
        self.product_table.setHorizontalHeaderLabels(headers)
        layout.addWidget(self.product_table)
        
        self.tab_widget.addTab(product_widget, "📦 商品分析")
    
    def setup_customer_tab(self):
        """取引先分析タブ設定"""
        customer_widget = QWidget()
        layout = QVBoxLayout(customer_widget)
        
        # グラフ
        self.customer_chart = SalesChart()
        layout.addWidget(self.customer_chart)
        
        # データテーブル
        self.customer_table = QTableWidget()
        self.customer_table.setMaximumHeight(250)
        headers = ["取引先名", "売上金額", "利用回数", "平均単価", "最終利用日"]
        self.customer_table.setColumnCount(len(headers))
        self.customer_table.setHorizontalHeaderLabels(headers)
        layout.addWidget(self.customer_table)
        
        self.tab_widget.addTab(customer_widget, "👥 取引先分析")
    
    def setup_report_tab(self):
        """レポート出力タブ設定"""
        report_widget = QWidget()
        layout = QVBoxLayout(report_widget)
        
        # レポートオプション
        options_group = QGroupBox("レポートオプション")
        options_layout = QFormLayout(options_group)
        
        self.include_graph_check = QCheckBox("グラフを含める")
        self.include_graph_check.setChecked(True)
        
        self.include_details_check = QCheckBox("詳細データを含める")
        self.include_details_check.setChecked(True)
        
        self.report_format_combo = QComboBox()
        self.report_format_combo.addItems(["PDF", "Excel", "CSV"])
        
        options_layout.addRow("グラフ:", self.include_graph_check)
        options_layout.addRow("詳細:", self.include_details_check)
        options_layout.addRow("形式:", self.report_format_combo)
        
        layout.addWidget(options_group)
        
        # 出力ボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.export_btn = QPushButton("レポート出力")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        button_layout.addWidget(self.export_btn)
        layout.addLayout(button_layout)
        
        # プレビューエリア
        self.report_preview = QTextEdit()
        self.report_preview.setReadOnly(True)
        self.report_preview.setPlaceholderText("レポートプレビューがここに表示されます...")
        layout.addWidget(self.report_preview)
        
        self.tab_widget.addTab(report_widget, "📄 レポート出力")
    
    def setup_connections(self):
        """シグナル接続"""
        self.analyze_btn.clicked.connect(self.refresh_data)
        self.period_combo.currentTextChanged.connect(self.update_date_range)
        self.export_btn.clicked.connect(self.export_report)
    
    def update_date_range(self):
        """期間選択に応じて日付範囲を更新"""
        period = self.period_combo.currentText()
        today = QDate.currentDate()
        
        if period == "過去12ヶ月":
            self.date_from.setDate(today.addMonths(-12))
            self.date_to.setDate(today)
        elif period == "過去6ヶ月":
            self.date_from.setDate(today.addMonths(-6))
            self.date_to.setDate(today)
        elif period == "過去3ヶ月":
            self.date_from.setDate(today.addMonths(-3))
            self.date_to.setDate(today)
        elif period == "今年":
            self.date_from.setDate(QDate(today.year(), 1, 1))
            self.date_to.setDate(today)
        elif period == "昨年":
            self.date_from.setDate(QDate(today.year() - 1, 1, 1))
            self.date_to.setDate(QDate(today.year() - 1, 12, 31))
    
    def refresh_data(self):
        """データ更新・分析実行"""
        try:
            # QDateからPython dateオブジェクトに変換
            qdate_from = self.date_from.date()
            qdate_to = self.date_to.date()
            date_from = date(qdate_from.year(), qdate_from.month(), qdate_from.day())
            date_to = date(qdate_to.year(), qdate_to.month(), qdate_to.day())
            
            # データ取得
            monthly_data = self.get_monthly_sales_data(date_from, date_to)
            product_data = self.get_product_analysis_data(date_from, date_to)
            customer_data = self.get_customer_analysis_data(date_from, date_to)
            
            # KPI更新
            self.update_kpi(monthly_data, product_data, customer_data)
            
            # グラフ更新
            self.summary_chart.plot_monthly_sales(monthly_data)
            self.monthly_chart.plot_monthly_sales(monthly_data)
            self.product_chart.plot_product_ranking(product_data)
            self.customer_chart.plot_customer_analysis(customer_data)
            
            # テーブル更新
            self.update_monthly_table(monthly_data)
            self.update_product_table(product_data)
            self.update_customer_table(customer_data)
            
            # レポートプレビュー更新
            self.update_report_preview(monthly_data, product_data, customer_data)
            
        except Exception as e:
            logger.error(f"データ分析エラー: {e}")
            QMessageBox.critical(self, "エラー", f"データ分析に失敗しました:\n{str(e)}")
    
    def get_monthly_sales_data(self, date_from: date, date_to: date) -> List[Dict[str, Any]]:
        """月別売上データ取得"""
        try:
            # datetimeオブジェクトに変換
            datetime_from = datetime.combine(date_from, datetime.min.time())
            datetime_to = datetime.combine(date_to, datetime.max.time())
            loans = db_manager.get_loans_for_period_all(datetime_from, datetime_to)
            
            monthly_data = {}
            for loan in loans:
                if loan.loan_date:  # loan_dateがnullでないことを確認
                    month_key = loan.loan_date.strftime("%Y-%m")
                    if month_key not in monthly_data:
                        monthly_data[month_key] = {
                            'month': loan.loan_date.strftime("%Y/%m"),
                            'total_sales': 0,
                            'loan_count': 0
                        }
                    
                    monthly_data[month_key]['total_sales'] += loan.total_amount or 0
                    monthly_data[month_key]['loan_count'] += 1
            
            # ソートして返却
            return sorted(monthly_data.values(), key=lambda x: x['month'])
            
        except Exception as e:
            logger.error(f"月別売上データ取得エラー: {e}")
            return []
    
    def get_product_analysis_data(self, date_from: date, date_to: date) -> List[Dict[str, Any]]:
        """商品分析データ取得"""
        try:
            # datetimeオブジェクトに変換
            datetime_from = datetime.combine(date_from, datetime.min.time())
            datetime_to = datetime.combine(date_to, datetime.max.time())
            loans = db_manager.get_loans_for_period_all(datetime_from, datetime_to)
            
            product_data = {}
            for loan in loans:
                product_id = loan.product_id
                if product_id and product_id not in product_data:
                    try:
                        product = db_manager.get_by_id(Product, product_id)
                        product_data[product_id] = {
                            'product_name': product.name if product else f'商品ID: {product_id}',
                            'total_sales': 0,
                            'loan_count': 0
                        }
                    except:
                        product_data[product_id] = {
                            'product_name': f'商品ID: {product_id}',
                            'total_sales': 0,
                            'loan_count': 0
                        }
                
                if product_id:
                    product_data[product_id]['total_sales'] += loan.total_amount or 0
                    product_data[product_id]['loan_count'] += 1
            
            # 売上順でソート
            return sorted(product_data.values(), key=lambda x: x['total_sales'], reverse=True)
            
        except Exception as e:
            logger.error(f"商品分析データ取得エラー: {e}")
            return []
    
    def get_customer_analysis_data(self, date_from: date, date_to: date) -> List[Dict[str, Any]]:
        """取引先分析データ取得"""
        try:
            # datetimeオブジェクトに変換
            datetime_from = datetime.combine(date_from, datetime.min.time())
            datetime_to = datetime.combine(date_to, datetime.max.time())
            loans = db_manager.get_loans_for_period_all(datetime_from, datetime_to)
            
            customer_data = {}
            for loan in loans:
                customer_id = loan.customer_id
                if customer_id and customer_id not in customer_data:
                    try:
                        customer = db_manager.get_by_id(Customer, customer_id)
                        customer_data[customer_id] = {
                            'customer_name': customer.name if customer else f'取引先ID: {customer_id}',
                            'total_sales': 0,
                            'loan_count': 0,
                            'last_loan_date': loan.loan_date or datetime.now()
                        }
                    except:
                        customer_data[customer_id] = {
                            'customer_name': f'取引先ID: {customer_id}',
                            'total_sales': 0,
                            'loan_count': 0,
                            'last_loan_date': loan.loan_date or datetime.now()
                        }
                
                if customer_id:
                    customer_data[customer_id]['total_sales'] += loan.total_amount or 0
                    customer_data[customer_id]['loan_count'] += 1
                    
                    # 最新貸出日更新
                    if loan.loan_date and loan.loan_date > customer_data[customer_id]['last_loan_date']:
                        customer_data[customer_id]['last_loan_date'] = loan.loan_date
            
            # 売上順でソート
            return sorted(customer_data.values(), key=lambda x: x['total_sales'], reverse=True)
            
        except Exception as e:
            logger.error(f"取引先分析データ取得エラー: {e}")
            return []
    
    def update_kpi(self, monthly_data: List[Dict], product_data: List[Dict], customer_data: List[Dict]):
        """KPI更新"""
        try:
            # 総売上
            total_sales = sum(item['total_sales'] for item in monthly_data)
            self.kpi_labels['total_sales'].setText(f"¥{total_sales:,.0f}")
            
            # 総貸出数
            total_loans = sum(item['loan_count'] for item in monthly_data)
            self.kpi_labels['total_loans'].setText(f"{total_loans}件")
            
            # 平均単価
            avg_per_loan = total_sales / total_loans if total_loans > 0 else 0
            self.kpi_labels['avg_per_loan'].setText(f"¥{avg_per_loan:,.0f}")
            
            # 利用客数
            active_customers = len(customer_data)
            self.kpi_labels['active_customers'].setText(f"{active_customers}社")
            
        except Exception as e:
            logger.error(f"KPI更新エラー: {e}")
    
    def update_monthly_table(self, data: List[Dict]):
        """月別テーブル更新"""
        self.monthly_table.setRowCount(len(data))
        
        for row, item in enumerate(data):
            self.monthly_table.setItem(row, 0, QTableWidgetItem(item['month']))
            self.monthly_table.setItem(row, 1, QTableWidgetItem(f"¥{item['total_sales']:,.0f}"))
            self.monthly_table.setItem(row, 2, QTableWidgetItem(str(item['loan_count'])))
            
            avg_price = item['total_sales'] / item['loan_count'] if item['loan_count'] > 0 else 0
            self.monthly_table.setItem(row, 3, QTableWidgetItem(f"¥{avg_price:,.0f}"))
            
            # 前月比（簡略実装）
            prev_month_change = "－"
            self.monthly_table.setItem(row, 4, QTableWidgetItem(prev_month_change))
    
    def update_product_table(self, data: List[Dict]):
        """商品テーブル更新"""
        self.product_table.setRowCount(len(data))
        
        total_sales = sum(item['total_sales'] for item in data)
        
        for row, item in enumerate(data):
            self.product_table.setItem(row, 0, QTableWidgetItem(item['product_name']))
            self.product_table.setItem(row, 1, QTableWidgetItem(f"¥{item['total_sales']:,.0f}"))
            self.product_table.setItem(row, 2, QTableWidgetItem(str(item['loan_count'])))
            
            avg_price = item['total_sales'] / item['loan_count'] if item['loan_count'] > 0 else 0
            self.product_table.setItem(row, 3, QTableWidgetItem(f"¥{avg_price:,.0f}"))
            
            share_rate = (item['total_sales'] / total_sales * 100) if total_sales > 0 else 0
            self.product_table.setItem(row, 4, QTableWidgetItem(f"{share_rate:.1f}%"))
    
    def update_customer_table(self, data: List[Dict]):
        """取引先テーブル更新"""
        self.customer_table.setRowCount(len(data))
        
        for row, item in enumerate(data):
            self.customer_table.setItem(row, 0, QTableWidgetItem(item['customer_name']))
            self.customer_table.setItem(row, 1, QTableWidgetItem(f"¥{item['total_sales']:,.0f}"))
            self.customer_table.setItem(row, 2, QTableWidgetItem(str(item['loan_count'])))
            
            avg_price = item['total_sales'] / item['loan_count'] if item['loan_count'] > 0 else 0
            self.customer_table.setItem(row, 3, QTableWidgetItem(f"¥{avg_price:,.0f}"))
            
            last_date = item['last_loan_date'].strftime("%Y/%m/%d")
            self.customer_table.setItem(row, 4, QTableWidgetItem(last_date))
    
    def update_report_preview(self, monthly_data: List[Dict], product_data: List[Dict], customer_data: List[Dict]):
        """レポートプレビュー更新"""
        date_from = self.date_from.date().toString("yyyy/MM/dd")
        date_to = self.date_to.date().toString("yyyy/MM/dd")
        
        # 総売上計算
        total_sales = sum(item['total_sales'] for item in monthly_data)
        total_loans = sum(item['loan_count'] for item in monthly_data)
        
        preview_text = f"""
売上分析レポート
期間: {date_from} ～ {date_to}
生成日時: {datetime.now().strftime("%Y/%m/%d %H:%M")}

【概要】
総売上金額: ¥{total_sales:,.0f}
総貸出件数: {total_loans}件
平均単価: ¥{total_sales/total_loans if total_loans > 0 else 0:,.0f}
利用客数: {len(customer_data)}社

【上位商品（売上金額）】
"""
        
        for i, item in enumerate(product_data[:5], 1):
            preview_text += f"{i}. {item['product_name']}: ¥{item['total_sales']:,.0f}\n"
        
        preview_text += "\n【上位取引先（売上金額）】\n"
        
        for i, item in enumerate(customer_data[:5], 1):
            preview_text += f"{i}. {item['customer_name']}: ¥{item['total_sales']:,.0f}\n"
        
        self.report_preview.setPlainText(preview_text)
    
    def export_report(self):
        """レポート出力"""
        try:
            format_type = self.report_format_combo.currentText()
            
            if format_type == "PDF":
                self.export_pdf_report()
            elif format_type == "Excel":
                self.export_excel_report()
            elif format_type == "CSV":
                self.export_csv_report()
                
        except Exception as e:
            logger.error(f"レポート出力エラー: {e}")
            QMessageBox.critical(self, "エラー", f"レポート出力に失敗しました:\n{str(e)}")
    
    def export_pdf_report(self):
        """PDF出力"""
        QMessageBox.information(self, "情報", "PDF出力機能は将来のバージョンで実装予定です。")
    
    def export_excel_report(self):
        """Excel出力"""
        QMessageBox.information(self, "情報", "Excel出力機能は将来のバージョンで実装予定です。")
    
    def export_csv_report(self):
        """CSV出力"""
        QMessageBox.information(self, "情報", "CSV出力機能は将来のバージョンで実装予定です。")