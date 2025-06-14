"""
ダッシュボードクラス
システムの概要とKPI表示
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                            QLabel, QPushButton, QFrame, QScrollArea, QProgressBar,
                            QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor
from typing import Dict, List, Any
import datetime

from ui.components.base_widget import BaseWidget
from core.config_manager import config_manager
from core.database import db_manager, Customer, Product, Loan, Invoice

# QtChartsのインポート（オプション）
try:
    from PyQt6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis
    QTCHARTS_AVAILABLE = True
except ImportError:
    QTCHARTS_AVAILABLE = False


class StatCard(BaseWidget):
    """統計カードウィジェット"""
    
    def __init__(self, title: str, value: str, icon: str = "📊", color: str = None):
        self.title = title
        self.value = value
        self.icon = icon
        self.color = color or "#2196F3"  # デフォルト色
        
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """UI初期化"""
        self.setFixedHeight(120)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # アイコンと値のレイアウト
        top_layout = QHBoxLayout()
        
        # アイコン
        icon_label = QLabel(self.icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 24))
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(icon_label)
        
        top_layout.addStretch()
        
        # 値
        value_label = QLabel(self.value)
        value_label.setFont(QFont("Yu Gothic UI", 20, QFont.Weight.Bold))
        value_label.setStyleSheet(f"color: {self.color};")
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        top_layout.addWidget(value_label)
        
        layout.addLayout(top_layout)
        
        # タイトル
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Yu Gothic UI", 12))
        title_label.setStyleSheet("color: #666;")
        layout.addWidget(title_label)
        
        # カードスタイル
        self.setStyleSheet(f"""
            StatCard {{
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }}
            StatCard:hover {{
                border-color: {self.color};
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
        """)
    
    def update_value(self, new_value: str):
        """値を更新"""
        self.value = new_value
        # 値ラベルを更新（子ウィジェットから検索）
        for child in self.findChildren(QLabel):
            if child.font().pointSize() == 20:  # 値ラベル
                child.setText(new_value)
                break


class QuickActionCard(BaseWidget):
    """クイックアクションカード"""
    
    action_clicked = pyqtSignal(str)
    
    def __init__(self, title: str, description: str, action_key: str, icon: str = "🚀"):
        self.title = title
        self.description = description
        self.action_key = action_key
        self.icon = icon
        
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """UI初期化"""
        self.setFixedHeight(100)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # アイコン
        icon_label = QLabel(self.icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 20))
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # テキスト部分
        text_layout = QVBoxLayout()
        
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        text_layout.addWidget(title_label)
        
        desc_label = QLabel(self.description)
        desc_label.setFont(QFont("Yu Gothic UI", 10))
        desc_label.setStyleSheet("color: #666;")
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # アクションボタン
        action_btn = QPushButton("実行")
        action_btn.clicked.connect(lambda: self.action_clicked.emit(self.action_key))
        action_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1976D2;
            }}
        """)
        layout.addWidget(action_btn)
        
        # カードスタイル
        self.setStyleSheet(f"""
            QuickActionCard {{
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }}
            QuickActionCard:hover {{
                border-color: #2196F3;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
        """)


class Dashboard(BaseWidget):
    """ダッシュボードウィジェット"""
    
    module_requested = pyqtSignal(str)
    
    def __init__(self):
        # Initialize data attributes first
        self._stats = {}
        self._chart_view = None
        self.last_update_label = None  # refresh()で使用される属性
        self.stat_cards = {}  # 統計カードを初期化
        self.alerts_layout = None  # アラートレイアウトを初期化
        
        super().__init__()
        # UIセットアップを先に実行
        self.setup_ui()
        # UIセットアップ後にデータを読み込み
        self.load_data()
        
        # 自動更新タイマー（負荷軽減のため2分間隔に変更）
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh)
        self.update_timer.start(120000)  # 2分ごとに更新
    
    def setup_ui(self):
        """UI初期化"""
        # メインレイアウト
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        
        # ヘッダー
        self.create_header(content_layout)
        
        # 統計カード
        self.create_stats_section(content_layout)
        
        # クイックアクション
        self.create_quick_actions(content_layout)
        
        # グラフとテーブル
        charts_layout = QHBoxLayout()
        
        # 売上グラフ
        self.create_sales_chart(charts_layout)
        
        # 最近のアクティビティ
        self.create_recent_activity(charts_layout)
        
        content_layout.addLayout(charts_layout)
        
        # アラート
        self.create_alerts_section(content_layout)
        
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # UIセットアップ完了
    
    def create_header(self, layout):
        """ヘッダー作成"""
        header_layout = QHBoxLayout()
        
        # タイトル
        title = QLabel("📊 ダッシュボード")
        title.setFont(QFont("Yu Gothic UI", 24, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 最終更新時刻
        self.last_update_label = QLabel(f"最終更新: {datetime.datetime.now().strftime('%H:%M')}")
        self.last_update_label.setStyleSheet("color: #666; font-size: 12px;")
        header_layout.addWidget(self.last_update_label)
        
        # 更新ボタン
        refresh_btn = QPushButton("🔄 更新")
        refresh_btn.clicked.connect(self.refresh)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
    
    def create_stats_section(self, layout):
        """統計セクション作成"""
        # セクションタイトル
        section_title = QLabel("📈 システム概要")
        section_title.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
        layout.addWidget(section_title)
        
        # 統計カードのグリッド
        stats_layout = QGridLayout()
        stats_layout.setSpacing(16)
        
        # 統計カード定義
        self.stat_cards = {
            "customers": StatCard("取引先数", "0", "👥", "#2196F3"),
            "products": StatCard("商品数", "0", "📦", "#9C27B0"),
            "active_loans": StatCard("貸出中", "0", "🛠", "#FF9800"),
            "pending_invoices": StatCard("未入金請求", "0", "💰", "#f44336"),
            "total_sales": StatCard("今月売上", "¥0", "📊", "#4CAF50"),
            "low_stock": StatCard("低在庫商品", "0", "⚠️", "#FF9800")
        }
        
        # カードを配置（3列）
        for i, (key, card) in enumerate(self.stat_cards.items()):
            row = i // 3
            col = i % 3
            stats_layout.addWidget(card, row, col)
        
        layout.addLayout(stats_layout)
    
    def create_quick_actions(self, layout):
        """クイックアクション作成"""
        # セクションタイトル
        section_title = QLabel("⚡ クイックアクション")
        section_title.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
        layout.addWidget(section_title)
        
        # アクションカード
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(16)
        
        actions = [
            ("新規貸出", "商品の貸出処理を開始", "loans", "🛠"),
            ("請求書作成", "月次請求書を生成", "invoices", "📄"),
            ("在庫確認", "在庫状況をチェック", "inventory", "📊"),
            ("売上レポート", "売上分析を表示", "analytics", "📈")
        ]
        
        for title, desc, key, icon in actions:
            card = QuickActionCard(title, desc, key, icon)
            card.action_clicked.connect(self.module_requested.emit)
            actions_layout.addWidget(card)
        
        layout.addLayout(actions_layout)
    
    def create_sales_chart(self, layout):
        """売上グラフ作成"""
        # グループボックス
        chart_group = QGroupBox("📈 月次売上推移")
        chart_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        chart_layout = QVBoxLayout(chart_group)
        
        # チャート作成
        if QTCHARTS_AVAILABLE:
            try:
                self._chart_view = self.create_bar_chart()
                chart_layout.addWidget(self._chart_view)
            except Exception as e:
                placeholder = QLabel(f"グラフ作成エラー: {e}")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("color: #666; font-size: 14px;")
                placeholder.setMinimumHeight(200)
                chart_layout.addWidget(placeholder)
        else:
            # QtChartsが利用できない場合はプレースホルダー
            placeholder = QLabel("グラフ表示（PyQt6.QtChartsが必要）")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #666; font-size: 14px;")
            placeholder.setMinimumHeight(200)
            chart_layout.addWidget(placeholder)
        
        chart_group.setMinimumWidth(400)
        layout.addWidget(chart_group)
    
    def create_bar_chart(self):
        """棒グラフ作成"""
        # バーシリーズ作成
        series = QBarSeries()
        
        # サンプルデータ（実際はDBから取得）
        months = ["1月", "2月", "3月", "4月", "5月", "6月"]
        values = [120000, 150000, 180000, 160000, 200000, 220000]
        
        bar_set = QBarSet("売上")
        for value in values:
            bar_set.append(value)
        
        series.append(bar_set)
        
        # チャート作成
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        # 軸設定
        axis_x = QBarCategoryAxis()
        axis_x.append(months)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setRange(0, max(values) * 1.2)
        axis_y.setTitleText("売上 (円)")
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
        
        # チャートビュー
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumHeight(200)
        
        return chart_view
    
    def create_recent_activity(self, layout):
        """最近のアクティビティ作成"""
        # グループボックス
        activity_group = QGroupBox("🕐 最近のアクティビティ")
        activity_group.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        activity_layout = QVBoxLayout(activity_group)
        
        # テーブル
        self.activity_table = QTableWidget(5, 3)
        self.activity_table.setHorizontalHeaderLabels(["時刻", "操作", "詳細"])
        
        # ヘッダーサイズ調整
        header = self.activity_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # サンプルデータ
        activities = [
            ("14:30", "貸出", "プロジェクター A社へ"),
            ("13:45", "返却", "スクリーン B社から"),
            ("12:20", "請求書", "2024年6月分 C社"),
            ("11:15", "在庫調整", "マイク +5個"),
            ("10:30", "新規登録", "顧客: D社")
        ]
        
        for row, (time, action, detail) in enumerate(activities):
            self.activity_table.setItem(row, 0, QTableWidgetItem(time))
            self.activity_table.setItem(row, 1, QTableWidgetItem(action))
            self.activity_table.setItem(row, 2, QTableWidgetItem(detail))
        
        self.activity_table.setMaximumHeight(200)
        activity_layout.addWidget(self.activity_table)
        
        activity_group.setMinimumWidth(400)
        layout.addWidget(activity_group)
    
    def create_alerts_section(self, layout):
        """アラートセクション作成"""
        # セクションタイトル
        section_title = QLabel("⚠️ 注意事項")
        section_title.setFont(QFont("Yu Gothic UI", 16, QFont.Weight.Bold))
        layout.addWidget(section_title)
        
        # アラートカード
        self.alerts_layout = QVBoxLayout()
        layout.addLayout(self.alerts_layout)
        
        # 初期アラート
        self.update_alerts()
    
    def create_alert_card(self, message: str, alert_type: str = "warning") -> QFrame:
        """アラートカード作成"""
        card = QFrame()
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        
        # アイコン
        icons = {
            "warning": "⚠️",
            "error": "❌",
            "info": "ℹ️",
            "success": "✅"
        }
        
        icon_label = QLabel(icons.get(alert_type, "⚠️"))
        icon_label.setFont(QFont("Segoe UI Emoji", 16))
        card_layout.addWidget(icon_label)
        
        # メッセージ
        msg_label = QLabel(message)
        msg_label.setFont(QFont("Yu Gothic UI", 12))
        msg_label.setWordWrap(True)
        card_layout.addWidget(msg_label)
        
        card_layout.addStretch()
        
        # スタイル
        colors = {
            "warning": self.get_theme_color("warning"),
            "error": self.get_theme_color("error"),
            "info": self.get_theme_color("primary"),
            "success": self.get_theme_color("success")
        }
        
        color = colors.get(alert_type, self.get_theme_color("warning"))
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color}33;
                border-left: 4px solid {color};
                border-radius: 4px;
            }}
        """)
        
        return card
    
    def load_data(self):
        """データを読み込み"""
        try:
            # 統計データ取得（エラーハンドリング強化）
            stats = db_manager.get_statistics()
            
            # 統計データが有効か確認
            if stats and isinstance(stats, dict):
                self._stats = stats
                self.update_stat_cards()
                self.update_alerts()
                print(f"ダッシュボードデータ更新完了: {stats}")
            else:
                print("統計データが無効です。デフォルト値を使用します。")
                self.handle_statistics_error("統計データが無効です")
            
        except Exception as e:
            print(f"ダッシュボードデータ読み込みエラー: {e}")
            self.handle_statistics_error(str(e))
    
    def handle_statistics_error(self, error_message: str):
        """統計取得エラー時の処理"""
        # デフォルト統計データを設定
        default_stats = {
            "customers_count": 0,
            "products_count": 0,
            "active_loans_count": 0,
            "total_loans_amount": 0,
            "pending_invoices_count": 0,
            "low_stock_products": 0
        }
        
        # 既存の統計データがある場合はそれを保持、なければデフォルトを使用
        if not hasattr(self, '_stats') or not self._stats:
            self._stats = default_stats
            print("デフォルト統計データを使用します")
        else:
            print("前回の統計データを保持します")
        
        # UIを更新
        self.update_stat_cards()
        self.update_alerts()
        
        # エラーメッセージを表示（ユーザーには軽い表現で）
        self.show_warning_message(f"データ更新に一時的な問題が発生しました: {error_message}")
    
    def update_stat_cards(self):
        """統計カードを更新"""
        # stat_cardsが初期化されているかチェック
        if not hasattr(self, 'stat_cards') or not self.stat_cards:
            return
            
        stats = self._stats
        
        # カード更新
        if "customers" in self.stat_cards:
            self.stat_cards["customers"].update_value(str(stats.get("customers_count", 0)))
        if "products" in self.stat_cards:
            self.stat_cards["products"].update_value(str(stats.get("products_count", 0)))
        if "active_loans" in self.stat_cards:
            self.stat_cards["active_loans"].update_value(str(stats.get("active_loans_count", 0)))
        if "pending_invoices" in self.stat_cards:
            self.stat_cards["pending_invoices"].update_value(str(stats.get("pending_invoices_count", 0)))
        
        # 売上計算（サンプル）
        total_amount = stats.get("total_loans_amount", 0)
        if "total_sales" in self.stat_cards:
            self.stat_cards["total_sales"].update_value(f"¥{total_amount:,.0f}")
        
        # 低在庫商品
        if "low_stock" in self.stat_cards:
            self.stat_cards["low_stock"].update_value(str(stats.get("low_stock_products", 0)))
    
    def update_alerts(self):
        """アラートを更新"""
        # alerts_layoutが初期化されているかチェック
        if not hasattr(self, 'alerts_layout') or self.alerts_layout is None:
            return
            
        # 既存のアラートを削除
        for i in reversed(range(self.alerts_layout.count())):
            child = self.alerts_layout.takeAt(i)
            if child.widget():
                child.widget().deleteLater()
        
        alerts = []
        
        # 低在庫アラート
        low_stock = self._stats.get("low_stock_products", 0)
        if low_stock > 0:
            alerts.append((f"{low_stock}個の商品が在庫不足です", "warning"))
        
        # 未入金アラート
        pending_invoices = self._stats.get("pending_invoices_count", 0)
        if pending_invoices > 0:
            alerts.append((f"{pending_invoices}件の未入金請求があります", "error"))
        
        # アラートがない場合
        if not alerts:
            alerts.append(("現在、注意すべき事項はありません", "success"))
        
        # アラートカード作成
        for message, alert_type in alerts:
            card = self.create_alert_card(message, alert_type)
            self.alerts_layout.addWidget(card)
    
    def refresh(self):
        """データを更新"""
        try:
            print("ダッシュボード更新開始...")
            self.load_data()
            if self.last_update_label:
                self.last_update_label.setText(f"最終更新: {datetime.datetime.now().strftime('%H:%M')}")
            print("ダッシュボード更新完了")
            # エラーが発生しなかった場合のみ成功メッセージ
            if hasattr(self, 'show_success_message'):
                self.show_success_message("ダッシュボードを更新しました")
        except Exception as e:
            print(f"ダッシュボード更新中にエラーが発生: {e}")
            # refresh()でエラーが発生した場合はload_data()内で既に処理されているため、
            # ここでは追加のエラーハンドリングのみ実行
            if self.last_update_label:
                self.last_update_label.setText(f"更新エラー: {datetime.datetime.now().strftime('%H:%M')}")
            
            # 重大なエラーの場合はタイマーを停止
            if hasattr(self, 'update_timer') and self.update_timer.isActive():
                print("重大なエラーのため自動更新を一時停止します")
                self.update_timer.stop()
                # 5分後に再開を試行
                QTimer.singleShot(300000, self.restart_timer)
    
    def restart_timer(self):
        """タイマーを再開"""
        try:
            if hasattr(self, 'update_timer'):
                print("自動更新タイマーを再開します")
                self.update_timer.start(120000)  # 2分間隔で再開
        except Exception as e:
            print(f"タイマー再開エラー: {e}")
    
    def showEvent(self, event):
        """表示時の処理"""
        try:
            super().showEvent(event)
            # フェードインアニメーション（安全にアニメーション実行）
            self.fade_in(500)
        except Exception as e:
            print(f"Dashboard showEvent エラー: {e}")
            # エラーが発生した場合は通常の表示処理を続行