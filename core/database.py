"""
データベース管理システム
SQLAlchemy を使用したモダンなORM実装
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool
from datetime import datetime
from typing import Optional, List, Any
from PyQt6.QtCore import QObject, pyqtSignal
import os
import sys
import logging
import traceback

Base = declarative_base()


# データモデル定義
class Customer(Base):
    """取引先モデル"""
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    postal_code = Column(String(10))
    phone = Column(String(20))
    fax = Column(String(20))
    email = Column(String(100))
    contact_person = Column(String(50))
    billing_date = Column(Integer)  # 請求締日
    closing_day = Column(Integer)  # 請求締日（別名）
    payment_terms = Column(Integer)  # 支払条件（日数）
    initial_fee_flag = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    loans = relationship("Loan", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")


class Product(Base):
    """商品モデル"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    model_number = Column(String(50))
    category = Column(String(50))  # カテゴリフィールドを追加
    daily_price = Column(Float, default=0)
    monthly_price = Column(Float, default=0)
    damage_fee = Column(Float, default=0)
    stock_quantity = Column(Integer, default=0)
    min_stock_level = Column(Integer, default=0)
    location = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    loans = relationship("Loan", back_populates="product")
    stock_adjustments = relationship("StockAdjustment", back_populates="product")
    invoice_details = relationship("InvoiceDetail", back_populates="product")


class Loan(Base):
    """貸出モデル"""
    __tablename__ = 'loans'
    
    id = Column(Integer, primary_key=True)
    loan_date = Column(DateTime, nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    return_date = Column(DateTime)
    status = Column(String(20), default='active')  # active, returned, overdue
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    customer = relationship("Customer", back_populates="loans")
    product = relationship("Product", back_populates="loans")


class StockAdjustment(Base):
    """在庫調整モデル"""
    __tablename__ = 'stock_adjustments'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    adjustment_type = Column(String(20), nullable=False)  # 増加, 減少, 入庫, 出庫
    quantity_change = Column(Integer, nullable=False)
    reason = Column(String(100))
    adjusted_by = Column(String(50))
    adjustment_date = Column(DateTime, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    product = relationship("Product", back_populates="stock_adjustments")


class Invoice(Base):
    """請求書モデル"""
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True)
    invoice_date = Column(DateTime, nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    billing_month = Column(String(7))  # YYYY-MM
    subtotal = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    tax_included = Column(Boolean, default=True)
    initial_fee = Column(Float, default=0)
    damage_fee = Column(Float, default=0)
    status = Column(String(20), default='draft')  # draft, sent, paid
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    customer = relationship("Customer", back_populates="invoices")
    details = relationship("InvoiceDetail", back_populates="invoice")


class InvoiceDetail(Base):
    """請求明細モデル"""
    __tablename__ = 'invoice_details'
    
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    
    # リレーション
    invoice = relationship("Invoice", back_populates="details")
    product = relationship("Product", back_populates="invoice_details")


class SystemLog(Base):
    """システムログモデル"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String(10))  # INFO, WARNING, ERROR
    module = Column(String(50))
    action = Column(String(100))
    user = Column(String(50))
    details = Column(Text)


class DatabaseManager(QObject):
    """データベース管理クラス"""
    
    # シグナル定義
    data_changed = pyqtSignal(str, str)  # table_name, action
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # EXEファイルと同じディレクトリにデータベースを作成
            if getattr(sys, 'frozen', False):
                # PyInstallerでビルドされた場合
                app_dir = os.path.dirname(sys.executable)
            else:
                # 開発環境の場合
                app_dir = os.path.dirname(os.path.abspath(__file__))
                app_dir = os.path.dirname(app_dir)  # プロジェクトルートに戻る
            
            db_path = os.path.join(app_dir, "business_system.db")
        super().__init__()
        self.db_path = db_path
        self.engine = None
        self.Session = None
        self._session = None
        
        # ログ設定
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # 統計データキャッシュ
        self._last_statistics = None
        self._statistics_cache_time = None
        
        self.initialize_database()
    
    def initialize_database(self):
        """データベースを初期化"""
        try:
            # データベースディレクトリの作成
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            # SQLite エンジンを作成
            self.engine = create_engine(
                f'sqlite:///{self.db_path}',
                poolclass=StaticPool,
                connect_args={'check_same_thread': False},
                echo=False  # デバッグ時はTrueに
            )
            
            # 接続テスト
            from sqlalchemy import text
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # セッションファクトリを作成
            self.Session = sessionmaker(bind=self.engine)
            
            # テーブルを作成
            Base.metadata.create_all(self.engine)
            
            print(f"データベースを初期化しました: {self.db_path}")
            return True
            
        except Exception as e:
            error_msg = f"データベース初期化エラー: {str(e)}"
            print(error_msg)
            if hasattr(self, 'error_occurred'):
                self.error_occurred.emit(error_msg)
            # 初期化失敗時も基本的なセッションファクトリは作成を試みる
            try:
                if not self.Session and self.engine:
                    self.Session = sessionmaker(bind=self.engine)
            except:
                pass
            return False
    
    def get_session(self) -> Session:
        """セッションを取得"""
        try:
            if self._session is None:
                if self.Session is None:
                    print("データベース再初期化を試行します...")
                    if not self.initialize_database():
                        raise Exception("データベース初期化に失敗しました")
                
                if self.Session is not None:
                    self._session = self.Session()
                    # テーブル存在確認
                    self._verify_tables()
                else:
                    raise Exception("データベースセッションファクトリが初期化されていません")
            return self._session
        except Exception as e:
            print(f"セッション取得エラー: {e}")
            print(f"データベースパス: {self.db_path}")
            # セッションをリセットして再試行
            self._session = None
            self.Session = None
            raise
    
    def _verify_tables(self):
        """テーブルの存在を確認"""
        try:
            from sqlalchemy import text, inspect
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()
            
            required_tables = ['customers', 'products', 'loans', 'invoices', 'invoice_details', 'stock_adjustments']
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if missing_tables:
                print(f"不足しているテーブル: {missing_tables}")
                print("テーブルを再作成します...")
                Base.metadata.create_all(self.engine)
                print("テーブル作成完了")
            else:
                print(f"既存テーブル確認完了: {existing_tables}")
                
        except Exception as e:
            print(f"テーブル確認エラー: {e}")
            # エラーが発生してもテーブル作成を試行
            try:
                Base.metadata.create_all(self.engine)
                print("フォールバックテーブル作成完了")
            except Exception as create_error:
                print(f"テーブル作成失敗: {create_error}")
    
    def close_session(self):
        """セッションを閉じる"""
        if self._session:
            self._session.close()
            self._session = None
    
    def create_backup(self, backup_path: Optional[str] = None) -> bool:
        """データベースのバックアップを作成"""
        try:
            import shutil
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backup_{timestamp}.db"
            
            shutil.copy2(self.db_path, backup_path)
            self.log_action("BACKUP", f"データベースバックアップ作成: {backup_path}")
            return True
            
        except Exception as e:
            error_msg = f"バックアップ作成エラー: {str(e)}"
            self.error_occurred.emit(error_msg)
            return False
    
    def optimize_database(self) -> bool:
        """データベースを最適化"""
        try:
            from sqlalchemy import text
            
            # SQLiteの場合は特別な処理
            if 'sqlite' in str(self.engine.url):
                # autocommitモードで実行
                with self.engine.connect() as conn:
                    # SQLiteではVACUUMは自動コミットされるため個別に実行
                    conn.execute(text("VACUUM"))
                    conn.execute(text("ANALYZE"))
            else:
                # その他のデータベース
                with self.engine.connect() as conn:
                    trans = conn.begin()
                    try:
                        conn.execute(text("VACUUM"))
                        conn.execute(text("ANALYZE"))
                        trans.commit()
                    except:
                        trans.rollback()
                        raise
            
            self.log_action("OPTIMIZE", "データベース最適化実行")
            return True
            
        except Exception as e:
            error_msg = f"データベース最適化エラー: {str(e)}"
            self.error_occurred.emit(error_msg)
            return False
    
    def log_action(self, action: str, details: str, level: str = "INFO", module: str = "SYSTEM"):
        """アクションをログに記録"""
        try:
            session = self.get_session()
            log_entry = SystemLog(
                level=level,
                module=module,
                action=action,
                details=details
            )
            session.add(log_entry)
            session.commit()
            
        except Exception as e:
            print(f"ログ記録エラー: {str(e)}")
    
    # CRUD操作のヘルパーメソッド
    def create(self, model_instance):
        """レコードを作成"""
        try:
            session = self.get_session()
            session.add(model_instance)
            session.commit()
            session.refresh(model_instance)
            
            table_name = model_instance.__tablename__
            self.data_changed.emit(table_name, "CREATE")
            self.log_action("CREATE", f"{table_name}にレコードを作成")
            
            return model_instance
            
        except Exception as e:
            session.rollback()
            error_msg = f"作成エラー: {str(e)}"
            self.error_occurred.emit(error_msg)
            return None
    
    def read(self, model_class, **filters):
        """レコードを読み取り"""
        try:
            session = self.get_session()
            query = session.query(model_class)
            
            for key, value in filters.items():
                if hasattr(model_class, key):
                    query = query.filter(getattr(model_class, key) == value)
            
            return query.all()
            
        except Exception as e:
            error_msg = f"読み取りエラー: {str(e)}"
            self.error_occurred.emit(error_msg)
            return []
    
    def get_all(self, model_class):
        """すべてのレコードを取得"""
        try:
            session = self.get_session()
            return session.query(model_class).all()
        except Exception as e:
            error_msg = f"全件取得エラー: {str(e)}"
            self.error_occurred.emit(error_msg)
            return []
    
    def search(self, model_class, **filters):
        """検索（readメソッドのエイリアス）"""
        return self.read(model_class, **filters)
    
    def get_loans_for_period_all(self, start_date, end_date):
        """期間内の貸出データを取得"""
        try:
            session = self.get_session()
            return session.query(Loan).filter(
                Loan.loan_date >= start_date,
                Loan.loan_date <= end_date
            ).all()
        except Exception as e:
            error_msg = f"期間別貸出データ取得エラー: {str(e)}"
            self.error_occurred.emit(error_msg)
            return []
    
    def update(self, model_instance, **updates):
        """レコードを更新"""
        try:
            session = self.get_session()
            
            for key, value in updates.items():
                if hasattr(model_instance, key):
                    setattr(model_instance, key, value)
            
            model_instance.updated_at = datetime.utcnow()
            session.commit()
            
            table_name = model_instance.__tablename__
            self.data_changed.emit(table_name, "UPDATE")
            self.log_action("UPDATE", f"{table_name}のレコードを更新")
            
            return model_instance
            
        except Exception as e:
            session.rollback()
            error_msg = f"更新エラー: {str(e)}"
            self.error_occurred.emit(error_msg)
            return None
    
    def delete(self, model_instance):
        """レコードを削除"""
        try:
            session = self.get_session()
            table_name = model_instance.__tablename__
            
            session.delete(model_instance)
            session.commit()
            
            self.data_changed.emit(table_name, "DELETE")
            self.log_action("DELETE", f"{table_name}のレコードを削除")
            
            return True
            
        except Exception as e:
            session.rollback()
            error_msg = f"削除エラー: {str(e)}"
            self.error_occurred.emit(error_msg)
            return False
    
    def get_statistics(self) -> dict:
        """システム統計を取得"""
        # キャッシュチェック（5分間有効）
        current_time = datetime.now()
        if (self._last_statistics is not None and 
            self._statistics_cache_time is not None and
            (current_time - self._statistics_cache_time).total_seconds() < 300):
            self.logger.debug("統計データをキャッシュから返却")
            return self._last_statistics
        
        self.logger.info("統計データの取得を開始")
        default_stats = {
            "customers_count": 0,
            "products_count": 0,
            "active_loans_count": 0,
            "total_loans_amount": 0,
            "pending_invoices_count": 0,
            "low_stock_products": 0
        }
        
        try:
            # データベース接続チェック
            if not self._check_database_connection():
                self.logger.error("データベース接続に失敗しました")
                return self._last_statistics or default_stats
            
            session = self.get_session()
            stats = {}
            
            # 基本統計を段階的に取得
            try:
                self.logger.debug("取引先数を取得中...")
                stats["customers_count"] = session.query(Customer).count()
                self.logger.debug(f"取引先数: {stats['customers_count']}")
            except Exception as e:
                self.logger.error(f"取引先数取得エラー: {str(e)}\n{traceback.format_exc()}")
                stats["customers_count"] = 0
            
            try:
                self.logger.debug("商品数を取得中...")
                stats["products_count"] = session.query(Product).count()
                self.logger.debug(f"商品数: {stats['products_count']}")
            except Exception as e:
                self.logger.error(f"商品数取得エラー: {str(e)}\n{traceback.format_exc()}")
                stats["products_count"] = 0
            
            try:
                self.logger.debug("アクティブな貸出数を取得中...")
                stats["active_loans_count"] = session.query(Loan).filter(Loan.status == 'active').count()
                self.logger.debug(f"アクティブ貸出数: {stats['active_loans_count']}")
            except Exception as e:
                self.logger.error(f"アクティブ貸出数取得エラー: {str(e)}\n{traceback.format_exc()}")
                stats["active_loans_count"] = 0
            
            try:
                self.logger.debug("貸出合計金額を計算中...")
                active_loans = session.query(Loan).filter(Loan.status == 'active').all()
                stats["total_loans_amount"] = sum(loan.total_amount or 0 for loan in active_loans)
                self.logger.debug(f"貸出合計金額: {stats['total_loans_amount']}")
            except Exception as e:
                self.logger.error(f"貸出合計金額計算エラー: {str(e)}\n{traceback.format_exc()}")
                stats["total_loans_amount"] = 0
            
            try:
                self.logger.debug("未払い請求書数を取得中...")
                # statusフィールドの存在を確認
                stats["pending_invoices_count"] = session.query(Invoice).filter(Invoice.status != 'paid').count()
                self.logger.debug(f"未払い請求書数: {stats['pending_invoices_count']}")
            except Exception as e:
                self.logger.warning(f"未払い請求書数取得でstatusフィールドエラー: {str(e)}")
                try:
                    # statusフィールドが存在しない場合は全請求書数
                    stats["pending_invoices_count"] = session.query(Invoice).count()
                    self.logger.debug(f"全請求書数（フォールバック）: {stats['pending_invoices_count']}")
                except Exception as e2:
                    self.logger.error(f"請求書数取得エラー: {str(e2)}\n{traceback.format_exc()}")
                    stats["pending_invoices_count"] = 0
            
            try:
                self.logger.debug("低在庫商品数を取得中...")
                stats["low_stock_products"] = session.query(Product).filter(
                    Product.stock_quantity <= Product.min_stock_level
                ).count()
                self.logger.debug(f"低在庫商品数: {stats['low_stock_products']}")
            except Exception as e:
                self.logger.error(f"低在庫商品数取得エラー: {str(e)}\n{traceback.format_exc()}")
                stats["low_stock_products"] = 0
            
            # キャッシュ更新
            self._last_statistics = stats
            self._statistics_cache_time = current_time
            
            self.logger.info(f"統計データ取得完了: {stats}")
            return stats
            
        except Exception as e:
            error_msg = f"統計取得で予期しないエラー: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.error_occurred.emit(error_msg)
            # エラー時はキャッシュまたはデフォルト値を返す
            return self._last_statistics or default_stats
    
    def _check_database_connection(self) -> bool:
        """データベース接続状態を確認"""
        try:
            if self.engine is None:
                self.logger.warning("データベースエンジンが初期化されていません")
                return False
            
            from sqlalchemy import text
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.logger.debug("データベース接続確認OK")
            return True
        except Exception as e:
            self.logger.error(f"データベース接続チェック失敗: {str(e)}")
            return False
    
    def search(self, model_class, search_term: str, search_fields: List[str]) -> List:
        """全文検索"""
        try:
            session = self.get_session()
            query = session.query(model_class)
            
            if search_term:
                conditions = []
                for field in search_fields:
                    if hasattr(model_class, field):
                        attr = getattr(model_class, field)
                        if hasattr(attr.type, 'python_type') and attr.type.python_type == str:
                            conditions.append(attr.like(f'%{search_term}%'))
                
                if conditions:
                    from sqlalchemy import or_
                    query = query.filter(or_(*conditions))
            
            return query.all()
            
        except Exception as e:
            error_msg = f"検索エラー: {str(e)}"
            self.error_occurred.emit(error_msg)
            return []


# グローバルデータベースマネージャインスタンス
db_manager = DatabaseManager()