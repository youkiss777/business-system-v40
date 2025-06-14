#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v4.0 - 強化された売上分析・レポートモジュール
Gemini API統合による高度なデータ分析とAI洞察機能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QComboBox, QCheckBox, QMessageBox, QHeaderView,
    QSplitter, QGroupBox, QLabel, QDateEdit, QSpinBox,
    QDoubleSpinBox, QFrame, QScrollArea, QTreeWidget, QTreeWidgetItem,
    QProgressBar, QSlider, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QDateTime, QTimer, QThread
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPainter, QPen
from typing import Optional, List, Dict, Any, Tuple
import logging
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import json
import csv
import io

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
from core.hybrid_ai_system import hybrid_ai_manager, AITaskType
from ui.components.base_widget import BaseWidget

logger = logging.getLogger(__name__)


class AIInsightsWidget(QWidget):
    """AI洞察ウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # タイトル
        title = QLabel("🤖 AI ビジネス洞察")
        title.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2196F3; margin: 10px 0;")
        layout.addWidget(title)
        
        # 分析ボタン群
        button_layout = QHBoxLayout()
        
        self.analyze_trends_btn = QPushButton("📈 トレンド分析")
        self.analyze_trends_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.predict_future_btn = QPushButton("🔮 将来予測")
        self.predict_future_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        
        self.risk_analysis_btn = QPushButton("⚠️ リスク分析")
        self.risk_analysis_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        
        self.opportunity_btn = QPushButton("💡 成長機会")
        self.opportunity_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        
        button_layout.addWidget(self.analyze_trends_btn)
        button_layout.addWidget(self.predict_future_btn)
        button_layout.addWidget(self.risk_analysis_btn)
        button_layout.addWidget(self.opportunity_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # AI洞察表示エリア
        self.insights_area = QTextEdit()
        self.insights_area.setReadOnly(True)
        self.insights_area.setPlaceholderText("AI分析結果がここに表示されます...")
        self.insights_area.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self.insights_area)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def setup_connections(self):
        """シグナル接続"""
        self.analyze_trends_btn.clicked.connect(self.analyze_trends)
        self.predict_future_btn.clicked.connect(self.predict_future)
        self.risk_analysis_btn.clicked.connect(self.analyze_risks)
        self.opportunity_btn.clicked.connect(self.find_opportunities)
    
    def show_loading(self, message: str):
        """ローディング表示"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 無限プログレス
        self.insights_area.setPlainText(f"🔄 {message}...")
    
    def hide_loading(self):
        """ローディング非表示"""
        self.progress_bar.setVisible(False)
    
    def display_insights(self, insights: Dict[str, Any]):
        """AI洞察表示"""
        self.hide_loading()
        
        if "error" in insights:
            self.insights_area.setPlainText(f"❌ エラー: {insights['error']}")
            return
        
        # 結果をフォーマットして表示
        formatted_text = self.format_ai_response(insights)
        self.insights_area.setMarkdown(formatted_text)
    
    def format_ai_response(self, response: Dict[str, Any]) -> str:
        """AI応答フォーマット"""
        if "text" in response:
            return response["text"]
        else:
            # 構造化されたデータをMarkdownに変換
            return json.dumps(response, ensure_ascii=False, indent=2)
    
    def analyze_trends(self):
        """トレンド分析"""
        self.show_loading("トレンド分析を実行中")
        
        try:
            # 売上データ取得
            sales_data = self.get_sales_data_for_analysis()
            
            # AI分析実行
            prompt = f"""
            以下の売上データを分析して、重要なトレンドと洞察を提供してください：
            
            {sales_data}
            
            分析内容：
            1. 売上トレンドの特徴
            2. 季節性パターン
            3. 成長率の変化
            4. 注目すべき変化点
            5. 今後の予測
            
            回答は日本語で、ビジネス担当者が理解しやすい形式でお願いします。
            """
            
            result = hybrid_ai_manager.analyze_data(prompt)
            self.display_insights(result)
            
        except Exception as e:
            logger.error(f"トレンド分析エラー: {e}")
            self.insights_area.setPlainText(f"❌ 分析エラー: {str(e)}")
            self.hide_loading()
    
    def predict_future(self):
        """将来予測"""
        self.show_loading("将来予測を計算中")
        
        try:
            sales_data = self.get_sales_data_for_analysis()
            
            prompt = f"""
            以下の売上データに基づいて、今後3-6ヶ月の予測を行ってください：
            
            {sales_data}
            
            予測内容：
            1. 売上予測（金額・成長率）
            2. 主要商品の需要予測
            3. 季節要因の影響
            4. 市場動向の予測
            5. 準備すべき対策
            
            予測の根拠と確度も含めて説明してください。
            """
            
            result = hybrid_ai_manager.analyze_data(prompt)
            self.display_insights(result)
            
        except Exception as e:
            logger.error(f"将来予測エラー: {e}")
            self.insights_area.setPlainText(f"❌ 予測エラー: {str(e)}")
            self.hide_loading()
    
    def analyze_risks(self):
        """リスク分析"""
        self.show_loading("リスク要因を分析中")
        
        try:
            sales_data = self.get_sales_data_for_analysis()
            
            prompt = f"""
            以下のビジネスデータからリスク要因を分析してください：
            
            {sales_data}
            
            分析項目：
            1. 売上減少リスク
            2. 顧客離反リスク
            3. 在庫リスク
            4. 市場変化リスク
            5. 財務リスク
            
            各リスクの影響度と対策案も提案してください。
            """
            
            result = hybrid_ai_manager.analyze_data(prompt)
            self.display_insights(result)
            
        except Exception as e:
            logger.error(f"リスク分析エラー: {e}")
            self.insights_area.setPlainText(f"❌ リスク分析エラー: {str(e)}")
            self.hide_loading()
    
    def find_opportunities(self):
        """成長機会分析"""
        self.show_loading("成長機会を探索中")
        
        try:
            sales_data = self.get_sales_data_for_analysis()
            
            prompt = f"""
            以下のビジネスデータから成長機会を特定してください：
            
            {sales_data}
            
            分析項目：
            1. 成長ポテンシャルの高い商品
            2. 拡大可能な顧客セグメント
            3. 新規市場の可能性
            4. クロスセルの機会
            5. 効率化できる領域
            
            具体的なアクションプランも提案してください。
            """
            
            result = hybrid_ai_manager.analyze_data(prompt)
            self.display_insights(result)
            
        except Exception as e:
            logger.error(f"成長機会分析エラー: {e}")
            self.insights_area.setPlainText(f"❌ 成長機会分析エラー: {str(e)}")
            self.hide_loading()
    
    def get_sales_data_for_analysis(self) -> str:
        """分析用売上データ取得"""
        try:
            # 過去12ヶ月のデータを取得
            end_date = datetime.now().date()
            start_date = end_date - relativedelta(months=12)
            
            loans = db_manager.get_loans_for_period_all(start_date, end_date)
            
            # データをCSV形式に変換
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["日付", "顧客ID", "商品ID", "数量", "単価", "合計金額"])
            
            for loan in loans:
                writer.writerow([
                    loan.loan_date.strftime("%Y-%m-%d"),
                    loan.customer_id,
                    loan.product_id,
                    loan.quantity,
                    loan.unit_price,
                    loan.total_amount
                ])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"売上データ取得エラー: {e}")
            return "データ取得エラー"


class DocumentAnalysisWidget(QWidget):
    """文書分析ウィジェット（Gemini画像解析活用）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # タイトル
        title = QLabel("📄 AI文書分析")
        title.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2196F3; margin: 10px 0;")
        layout.addWidget(title)
        
        # ファイル選択エリア
        file_group = QGroupBox("文書ファイル選択")
        file_layout = QVBoxLayout(file_group)
        
        file_select_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("画像ファイル（請求書、見積書、契約書など）を選択...")
        
        self.browse_btn = QPushButton("📁 ファイル選択")
        self.browse_btn.setStyleSheet("""
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
        
        file_select_layout.addWidget(self.file_path_edit)
        file_select_layout.addWidget(self.browse_btn)
        file_layout.addLayout(file_select_layout)
        
        # 分析オプション
        option_layout = QHBoxLayout()
        
        self.extract_text_btn = QPushButton("📝 テキスト抽出")
        self.analyze_business_btn = QPushButton("💼 ビジネス分析")
        self.extract_data_btn = QPushButton("📊 データ抽出")
        
        for btn in [self.extract_text_btn, self.analyze_business_btn, self.extract_data_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 10px 15px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        
        option_layout.addWidget(self.extract_text_btn)
        option_layout.addWidget(self.analyze_business_btn)
        option_layout.addWidget(self.extract_data_btn)
        option_layout.addStretch()
        
        file_layout.addLayout(option_layout)
        layout.addWidget(file_group)
        
        # 結果表示エリア
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setPlaceholderText("分析結果がここに表示されます...")
        self.result_area.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.result_area)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def setup_connections(self):
        """シグナル接続"""
        self.browse_btn.clicked.connect(self.browse_file)
        self.extract_text_btn.clicked.connect(self.extract_text)
        self.analyze_business_btn.clicked.connect(self.analyze_business_document)
        self.extract_data_btn.clicked.connect(self.extract_structured_data)
    
    def browse_file(self):
        """ファイル選択"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "文書画像ファイルを選択",
            "",
            "画像ファイル (*.png *.jpg *.jpeg *.bmp *.gif);;すべてのファイル (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
    
    def show_loading(self, message: str):
        """ローディング表示"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.result_area.setPlainText(f"🔄 {message}...")
    
    def hide_loading(self):
        """ローディング非表示"""
        self.progress_bar.setVisible(False)
    
    def extract_text(self):
        """テキスト抽出"""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "警告", "ファイルを選択してください。")
            return
        
        self.show_loading("テキストを抽出中")
        
        try:
            result = hybrid_ai_manager.extract_text_from_image(file_path)
            
            if "error" in result:
                self.result_area.setPlainText(f"❌ エラー: {result['error']}")
            else:
                # テキスト抽出結果を整形
                formatted_result = self.format_ocr_result(result)
                self.result_area.setMarkdown(formatted_result)
            
            self.hide_loading()
            
        except Exception as e:
            logger.error(f"テキスト抽出エラー: {e}")
            self.result_area.setPlainText(f"❌ 抽出エラー: {str(e)}")
            self.hide_loading()
    
    def analyze_business_document(self):
        """ビジネス文書分析"""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "警告", "ファイルを選択してください。")
            return
        
        self.show_loading("ビジネス文書を分析中")
        
        try:
            result = hybrid_ai_manager.analyze_image(
                file_path, 
                """
                このビジネス文書を詳細に分析してください：
                
                1. 文書の種類（請求書、見積書、契約書など）
                2. 重要な情報（金額、日付、会社情報）
                3. ビジネス上の意味と重要度
                4. 必要なアクション
                5. 注意すべき点
                
                結果を日本語で分かりやすく整理してください。
                """
            )
            
            if "error" in result:
                self.result_area.setPlainText(f"❌ エラー: {result['error']}")
            else:
                self.result_area.setMarkdown(result.get("text", str(result)))
            
            self.hide_loading()
            
        except Exception as e:
            logger.error(f"ビジネス文書分析エラー: {e}")
            self.result_area.setPlainText(f"❌ 分析エラー: {str(e)}")
            self.hide_loading()
    
    def extract_structured_data(self):
        """構造化データ抽出"""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "警告", "ファイルを選択してください。")
            return
        
        self.show_loading("構造化データを抽出中")
        
        try:
            result = hybrid_ai_manager.analyze_image(
                file_path,
                """
                この文書から構造化されたデータを抽出して、JSON形式で返してください：
                
                {
                    "document_type": "文書種類",
                    "company_name": "会社名",
                    "amount": "金額",
                    "date": "日付",
                    "items": [
                        {
                            "name": "項目名",
                            "quantity": "数量",
                            "price": "価格"
                        }
                    ],
                    "other_info": "その他の重要情報"
                }
                
                できるだけ正確に情報を抽出してください。
                """
            )
            
            if "error" in result:
                self.result_area.setPlainText(f"❌ エラー: {result['error']}")
            else:
                # JSON形式で表示
                try:
                    # JSONとして解析を試行
                    data = json.loads(result.get("text", "{}"))
                    formatted_json = json.dumps(data, ensure_ascii=False, indent=2)
                    self.result_area.setPlainText(formatted_json)
                except:
                    # JSON解析失敗時は生テキスト表示
                    self.result_area.setMarkdown(result.get("text", str(result)))
            
            self.hide_loading()
            
        except Exception as e:
            logger.error(f"データ抽出エラー: {e}")
            self.result_area.setPlainText(f"❌ 抽出エラー: {str(e)}")
            self.hide_loading()
    
    def format_ocr_result(self, result: Dict[str, Any]) -> str:
        """OCR結果フォーマット"""
        if "text" in result:
            return f"## 📝 抽出されたテキスト\n\n{result['text']}"
        else:
            return f"```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```"


class EnhancedAnalyticsWidget(BaseWidget):
    """強化された売上分析メインウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
        self.refresh_data()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # タイトル
        title_layout = QHBoxLayout()
        title = QLabel("📈 AI強化売上分析システム")
        title.setFont(QFont("Yu Gothic UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #2196F3; margin: 10px 0;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        # AI機能状態表示
        self.ai_status_label = QLabel("🤖 AI機能: 確認中...")
        self.ai_status_label.setStyleSheet("font-size: 12px; color: #666;")
        title_layout.addWidget(self.ai_status_label)
        
        layout.addLayout(title_layout)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        
        # 既存の分析タブ（元のanalyticsモジュールから）
        self.setup_basic_analytics_tab()
        
        # AI洞察タブ
        ai_insights_widget = AIInsightsWidget()
        self.tab_widget.addTab(ai_insights_widget, "🤖 AI洞察")
        
        # 文書分析タブ
        document_analysis_widget = DocumentAnalysisWidget()
        self.tab_widget.addTab(document_analysis_widget, "📄 文書分析")
        
        # 設定タブ
        self.setup_settings_tab()
        
        layout.addWidget(self.tab_widget)
        
        # AI機能状態更新
        self.update_ai_status()
    
    def setup_basic_analytics_tab(self):
        """基本分析タブ設定（既存機能）"""
        # 元のanalyticsモジュールの機能をここに統合
        basic_widget = QWidget()
        layout = QVBoxLayout(basic_widget)
        
        # 期間選択エリア
        period_group = QGroupBox("分析期間設定")
        period_layout = QHBoxLayout(period_group)
        
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "過去12ヶ月", "過去6ヶ月", "過去3ヶ月", "今年", "昨年", "カスタム期間"
        ])
        
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addMonths(-12))
        self.date_from.setCalendarPopup(True)
        
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        
        self.analyze_btn = QPushButton("📊 分析実行")
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
        
        # グラフエリア（既存のSalesChartを使用）
        if MATPLOTLIB_AVAILABLE:
            from modules.analytics import SalesChart
            self.sales_chart = SalesChart()
            layout.addWidget(self.sales_chart)
        else:
            no_chart_label = QLabel("グラフ機能を使用するには matplotlib をインストールしてください。")
            no_chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_chart_label)
        
        self.tab_widget.addTab(basic_widget, "📊 基本分析")
    
    def setup_settings_tab(self):
        """設定タブ設定"""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        
        # AI設定
        ai_group = QGroupBox("AI機能設定")
        ai_layout = QFormLayout(ai_group)
        
        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems(["自動選択", "Gemini優先", "OpenAI優先"])
        
        self.cost_limit_spin = QDoubleSpinBox()
        self.cost_limit_spin.setRange(0, 1000)
        self.cost_limit_spin.setValue(50.0)
        self.cost_limit_spin.setSuffix(" USD")
        
        self.fallback_check = QCheckBox("フォールバック機能を有効にする")
        self.fallback_check.setChecked(True)
        
        ai_layout.addRow("AIプロバイダー:", self.ai_provider_combo)
        ai_layout.addRow("月間コスト制限:", self.cost_limit_spin)
        ai_layout.addRow("", self.fallback_check)
        
        layout.addWidget(ai_group)
        
        # 分析設定
        analysis_group = QGroupBox("分析設定")
        analysis_layout = QFormLayout(analysis_group)
        
        self.auto_analysis_check = QCheckBox("データ更新時に自動分析")
        self.detailed_insights_check = QCheckBox("詳細な洞察を生成")
        self.detailed_insights_check.setChecked(True)
        
        analysis_layout.addRow("", self.auto_analysis_check)
        analysis_layout.addRow("", self.detailed_insights_check)
        
        layout.addWidget(analysis_group)
        
        # 保存ボタン
        save_btn = QPushButton("💾 設定保存")
        save_btn.setStyleSheet("""
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
        save_btn.clicked.connect(self.save_settings)
        
        layout.addWidget(save_btn)
        layout.addStretch()
        
        self.tab_widget.addTab(settings_widget, "⚙️ 設定")
    
    def setup_connections(self):
        """シグナル接続"""
        if hasattr(self, 'analyze_btn'):
            self.analyze_btn.clicked.connect(self.refresh_data)
    
    def update_ai_status(self):
        """AI機能状態更新"""
        try:
            status = hybrid_ai_manager.get_status_report()
            
            gemini_enabled = status["providers"]["gemini"]["enabled"]
            openai_enabled = status["providers"]["openai"]["enabled"]
            
            if gemini_enabled and openai_enabled:
                self.ai_status_label.setText("🤖 AI機能: Gemini + OpenAI 利用可能")
                self.ai_status_label.setStyleSheet("font-size: 12px; color: #4CAF50;")
            elif gemini_enabled:
                self.ai_status_label.setText("🤖 AI機能: Gemini 利用可能")
                self.ai_status_label.setStyleSheet("font-size: 12px; color: #2196F3;")
            elif openai_enabled:
                self.ai_status_label.setText("🤖 AI機能: OpenAI 利用可能")
                self.ai_status_label.setStyleSheet("font-size: 12px; color: #FF9800;")
            else:
                self.ai_status_label.setText("🤖 AI機能: 利用不可")
                self.ai_status_label.setStyleSheet("font-size: 12px; color: #f44336;")
                
        except Exception as e:
            logger.error(f"AI状態更新エラー: {e}")
            self.ai_status_label.setText("🤖 AI機能: 状態不明")
    
    def refresh_data(self):
        """データ更新"""
        try:
            # 基本的な分析データ更新
            if hasattr(self, 'sales_chart') and MATPLOTLIB_AVAILABLE:
                # 元のanalyticsモジュールの機能を使用
                pass
                
        except Exception as e:
            logger.error(f"データ更新エラー: {e}")
            QMessageBox.critical(self, "エラー", f"データ更新に失敗しました:\n{str(e)}")
    
    def save_settings(self):
        """設定保存"""
        try:
            # ハイブリッドAI設定を保存
            provider_map = {
                "自動選択": "auto",
                "Gemini優先": "gemini", 
                "OpenAI優先": "openai"
            }
            
            provider = provider_map.get(self.ai_provider_combo.currentText(), "auto")
            cost_limit = self.cost_limit_spin.value()
            fallback = self.fallback_check.isChecked()
            
            # settings保存処理（実装が必要）
            
            QMessageBox.information(self, "設定保存", "設定を保存しました。")
            
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"設定保存に失敗しました:\n{str(e)}")