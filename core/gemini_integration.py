#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v4.0 - Google Gemini API統合機能
画像・音声・動画・大容量データ処理対応のAI機能
"""

import os
import json
import logging
import time
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import base64
from datetime import datetime, timedelta

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import PIL.Image
    from PIL import ImageEnhance, ImageFilter
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

from PyQt6.QtCore import QSettings, QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class GeminiClient:
    """Google Gemini APIクライアント"""
    
    def __init__(self):
        self.settings = QSettings("BusinessSystem", "GeminiAPI")
        self.api_key = ""
        self.model_name = "gemini-2.5-pro-exp-03-25"
        self.enabled = False
        self.model = None
        
        # 環境変数ファイル読み込み
        self._load_env_file()
        
        # 使用量カウンター（コスト最適化用）
        self.monthly_token_usage = 0
        self.monthly_limit = 1000000  # 無料枠: 100万トークン/月
        
        # レート制限管理
        self.requests_per_minute = 0
        self.requests_per_day = 0
        self.last_request_time = datetime.now()
        self.rate_limit_reset_time = datetime.now() + timedelta(minutes=1)
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # リトライ設定
        self.max_retries = 3
        self.retry_delays = [2, 5, 10]  # 秒
        
        # レート制限による一時無効化
        self.rate_limit_disabled = False
        self.rate_limit_disable_until = None
        
        # 設定読み込み
        self.load_settings()
        
        # Gemini初期化
        if GEMINI_AVAILABLE and self.api_key:
            self.initialize_gemini()
    
    def _load_env_file(self):
        """環境変数ファイル読み込み"""
        try:
            from pathlib import Path
            # 複数の環境変数ファイルを確認
            env_files = [
                Path(__file__).parent.parent / "config" / "ai_settings.env",
                Path(__file__).parent.parent / "config" / ".env",
            ]
            
            for env_file in env_files:
                if env_file.exists():
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                os.environ[key] = value
                    logger.info(f"環境変数ファイル読み込み完了: {env_file}")
                    break
        except Exception as e:
            logger.warning(f"環境変数ファイル読み込みエラー: {e}")
    
    def load_settings(self):
        """設定読み込み"""
        try:
            # 環境変数から読み込み（優先）
            self.api_key = os.environ.get("GEMINI_API_KEY", "")
            self.model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25")
            
            # QSettingsからフォールバック（環境変数が優先）
            if not self.api_key:
                self.api_key = self.settings.value("api_key", "", str)
            
            # 環境変数でモデルが設定されていない場合のみQSettingsを使用
            env_model = os.environ.get("GEMINI_MODEL", "")
            if not env_model:
                saved_model = self.settings.value("model_name", "gemini-2.5-pro-exp-03-25", str)
                self.model_name = saved_model
            # 環境変数がある場合はそちらを優先（既に設定済み）
                    
            self.monthly_token_usage = self.settings.value("monthly_token_usage", 0, int)
            
            logger.info(f"Gemini設定読み込み完了: モデル={self.model_name}, APIキー={'設定済み' if self.api_key else '未設定'}")
        except Exception as e:
            logger.error(f"Gemini設定読み込みエラー: {e}")
    
    def save_settings(self):
        """設定保存（QSettings + 環境変数ファイル）"""
        try:
            # QSettingsに保存
            self.settings.setValue("api_key", self.api_key)
            self.settings.setValue("model_name", self.model_name)
            self.settings.setValue("monthly_token_usage", self.monthly_token_usage)
            self.settings.setValue("requests_per_day", self.requests_per_day)
            
            # 環境変数ファイルにも保存（永続化）
            self._save_to_env_file()
            
            logger.info(f"Gemini設定保存完了: モデル={self.model_name}")
        except Exception as e:
            logger.error(f"Gemini設定保存エラー: {e}")
    
    def _save_to_env_file(self):
        """環境変数ファイルに設定保存"""
        try:
            from pathlib import Path
            env_file = Path(__file__).parent.parent / "config" / "ai_settings.env"
            
            if not env_file.exists():
                # ファイルが存在しない場合はテンプレートからコピー
                template_file = env_file.with_name("ai_settings.env.template")
                if template_file.exists():
                    import shutil
                    shutil.copy2(template_file, env_file)
                    logger.info(f"環境変数ファイルをテンプレートから作成: {env_file}")
            
            # 既存の設定を読み込み
            lines = []
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            
            # GEMINI_MODEL設定を更新または追加
            model_updated = False
            for i, line in enumerate(lines):
                if line.startswith('GEMINI_MODEL='):
                    lines[i] = f'GEMINI_MODEL={self.model_name}\n'
                    model_updated = True
                    break
            
            if not model_updated:
                # GEMINI_API_KEYの後に追加
                for i, line in enumerate(lines):
                    if line.startswith('GEMINI_API_KEY='):
                        lines.insert(i + 1, f'GEMINI_MODEL={self.model_name}\n')
                        break
                else:
                    # 見つからない場合は末尾に追加
                    lines.append(f'GEMINI_MODEL={self.model_name}\n')
            
            # ファイルに書き込み
            with open(env_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            logger.info(f"環境変数ファイル更新完了: {env_file}")
            
        except Exception as e:
            logger.warning(f"環境変数ファイル保存エラー: {e}")
    
    def switch_to_flash_model(self):
        """軽量なFlashモデルに切り替え"""
        # 現在のモデルに応じて適切な軽量モデルに切り替え
        if "2.5" in self.model_name:
            target_model = "gemini-2.5-flash-preview-05-20"  # 最新の2.5系Flash版
        elif "2.0" in self.model_name:
            target_model = "gemini-2.0-flash"
        else:
            target_model = "gemini-1.5-flash-8b"  # 最軽量
            
        if self.model_name != target_model:
            logger.info(f"レート制限のため{self.model_name}から{target_model}に切り替えます")
            self.model_name = target_model
            self.initialize_gemini()
            self.save_settings()
            return True
        return False
    
    def get_available_models(self) -> List[str]:
        """利用可能なモデル一覧"""
        return [
            # === Gemini 2.5 (最新) ===
            "gemini-2.5-pro-exp-03-25",           # 最新実験版
            "gemini-2.5-pro-preview-03-25",       # 最新プレビュー版
            "gemini-2.5-flash-preview-04-17",     # 高速版
            "gemini-2.5-flash-preview-05-20",     # 改良版高速
            
            # === Gemini 2.0 (推奨) ===
            "gemini-2.0-flash-exp",               # 実験版（推奨）
            "gemini-2.0-flash",                   # 安定版
            "gemini-2.0-pro-exp",                 # Pro実験版
            "gemini-2.0-flash-thinking-exp",      # 思考型
            
            # === Gemini 1.5 (従来) ===
            "gemini-1.5-pro",                     # 高性能、制限厳しい
            "gemini-1.5-flash",                   # 軽量、制限緩い
            "gemini-1.5-flash-8b",                # 超軽量版
            
            # === レガシー ===
            "gemini-1.0-pro"                     # 旧世代、安定
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """現在のステータスを取得"""
        now = datetime.now()
        return {
            "enabled": self.enabled,
            "api_available": GEMINI_AVAILABLE,
            "rate_limit_disabled": self.rate_limit_disabled,
            "disable_until": self.rate_limit_disable_until.isoformat() if self.rate_limit_disable_until else None,
            "current_model": self.model_name,
            "requests_per_minute": self.requests_per_minute,
            "requests_per_day": self.requests_per_day,
            "monthly_token_usage": self.monthly_token_usage,
            "monthly_limit": self.monthly_limit,
            "usage_percentage": (self.monthly_token_usage / self.monthly_limit) * 100
        }
    
    def initialize_gemini(self):
        """Gemini API初期化"""
        try:
            genai.configure(api_key=self.api_key)
            
            # 安全設定
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # モデル初期化
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                safety_settings=safety_settings
            )
            
            self.enabled = True
            logger.info(f"Gemini API初期化完了: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Gemini API初期化エラー: {e}")
            self.enabled = False
    
    def set_api_key(self, api_key: str):
        """APIキー設定"""
        self.api_key = api_key
        self.save_settings()
        
        if GEMINI_AVAILABLE and api_key:
            self.initialize_gemini()
    
    def is_enabled(self) -> bool:
        """利用可能状態確認"""
        if self.rate_limit_disabled:
            return False
        return self.enabled and GEMINI_AVAILABLE
    
    def check_usage_limit(self) -> bool:
        """使用量制限チェック"""
        return self.monthly_token_usage < self.monthly_limit
    
    def estimate_tokens(self, content: Union[str, List]) -> int:
        """トークン数推定（概算）"""
        if isinstance(content, str):
            # 日本語: 約2文字=1トークン、英語: 約4文字=1トークン
            japanese_chars = len([c for c in content if ord(c) > 255])
            other_chars = len(content) - japanese_chars
            return japanese_chars // 2 + other_chars // 4
        elif isinstance(content, list):
            total = 0
            for item in content:
                if isinstance(item, str):
                    total += self.estimate_tokens(item)
                elif hasattr(item, 'size'):  # 画像の場合
                    total += 258  # Geminiの画像処理基本トークン数
            return total
        return 0
    
    def check_rate_limits(self) -> bool:
        """レート制限チェック"""
        now = datetime.now()
        
        # 一時無効化チェック
        if self.rate_limit_disabled:
            if self.rate_limit_disable_until and now < self.rate_limit_disable_until:
                return False
            else:
                # 無効化期間終了
                self.rate_limit_disabled = False
                self.rate_limit_disable_until = None
                logger.info("Gemini API レート制限の一時無効化を解除しました")
        
        # 分単位リセット
        if now >= self.rate_limit_reset_time:
            self.requests_per_minute = 0
            self.rate_limit_reset_time = now + timedelta(minutes=1)
        
        # 日単位リセット
        if now >= self.daily_reset_time:
            self.requests_per_day = 0
            self.daily_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # 無料枠制限チェック（分間15リクエスト、日間1500リクエスト）
        if self.requests_per_minute >= 15 or self.requests_per_day >= 1500:
            return False
        
        return True
    
    def disable_temporarily(self, duration_minutes: int = 30):
        """レート制限により一時的に無効化"""
        self.rate_limit_disabled = True
        self.rate_limit_disable_until = datetime.now() + timedelta(minutes=duration_minutes)
        logger.warning(f"Gemini API を{duration_minutes}分間一時無効化しました")
    
    def wait_for_rate_limit(self):
        """レート制限待機"""
        now = datetime.now()
        if self.requests_per_minute >= 15:
            wait_time = (self.rate_limit_reset_time - now).total_seconds()
            if wait_time > 0:
                logger.info(f"レート制限により{wait_time:.1f}秒待機します")
                time.sleep(wait_time)
    
    def generate_content(self, prompt: Union[str, List], **kwargs) -> Dict[str, Any]:
        """コンテンツ生成（レート制限対応）"""
        if not self.is_enabled():
            return {"error": "Gemini APIが利用できません"}
        
        if not self.check_usage_limit():
            return {"error": "月間利用制限に達しました"}
        
        # レート制限チェック
        if not self.check_rate_limits():
            self.wait_for_rate_limit()
            if not self.check_rate_limits():
                return {"error": "レート制限により一時的に利用できません。しばらく待ってから再試行してください。"}
        
        # リトライ機能付き実行
        for attempt in range(self.max_retries):
            try:
                # トークン数推定
                estimated_tokens = self.estimate_tokens(prompt)
                
                # 生成実行
                response = self.model.generate_content(prompt, **kwargs)
                
                # 成功時の処理
                self.monthly_token_usage += estimated_tokens
                self.requests_per_minute += 1
                self.requests_per_day += 1
                self.save_settings()
                
                return {
                    "text": response.text,
                    "usage": {
                        "estimated_tokens": estimated_tokens,
                        "monthly_total": self.monthly_token_usage,
                        "remaining": self.monthly_limit - self.monthly_token_usage,
                        "requests_today": self.requests_per_day
                    }
                }
                
            except Exception as e:
                error_str = str(e)
                
                # レート制限エラーの処理
                if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                    # 最初のレート制限エラー時にFlashモデルに自動切り替え
                    if attempt == 0 and self.switch_to_flash_model():
                        logger.info("Flashモデルに切り替えてリトライします")
                        time.sleep(2)
                        continue
                    
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delays[attempt]
                        logger.warning(f"レート制限エラー。{wait_time}秒後にリトライします (試行 {attempt + 1}/{self.max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        # 深刻なレート制限の場合は一時無効化
                        if "GenerateRequestsPerDayPerProjectPerModel" in error_str:
                            self.disable_temporarily(120)  # 2時間無効化
                        else:
                            self.disable_temporarily(30)   # 30分無効化
                        
                        return {
                            "error": "レート制限エラー: 無料枠の制限に達しました。\n"
                                   "Gemini APIは一時的に無効化されます。\n"
                                   "システムはOpenAI APIにフォールバックします。\n\n"
                                   "対処法：\n"
                                   "1. しばらく時間をおいて自動回復を待つ\n"
                                   "2. より軽量なgemini-1.5-flashモデルに切り替え\n"
                                   "3. 有料プランへのアップグレードを検討",
                            "error_type": "rate_limit",
                            "retry_after": 60,
                            "current_model": self.model_name,
                            "temporarily_disabled": True
                        }
                
                # その他のエラー
                logger.error(f"Gemini生成エラー (試行 {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    return {"error": f"生成エラー: {error_str}"}
                else:
                    time.sleep(1)  # 短い待機
    
    def analyze_image(self, image_path: str, prompt: str = "") -> Dict[str, Any]:
        """画像分析"""
        if not IMAGE_PROCESSING_AVAILABLE:
            return {"error": "画像処理ライブラリが利用できません"}
        
        try:
            image = PIL.Image.open(image_path)
            
            if not prompt:
                prompt = """
                この画像を詳細に分析して、以下の情報をJSONで返してください：
                {
                    "画像種類": "写真/図面/文書/その他",
                    "主要オブジェクト": ["オブジェクト1", "オブジェクト2"],
                    "テキスト内容": "抽出されたテキスト",
                    "業務関連情報": "ビジネス文脈での重要情報",
                    "推奨アクション": "この画像に基づく推奨操作"
                }
                """
            
            return self.generate_content([prompt, image])
            
        except Exception as e:
            logger.error(f"画像分析エラー: {e}")
            return {"error": f"画像分析エラー: {str(e)}"}
    
    def extract_text_from_image(self, image_path: str) -> Dict[str, Any]:
        """画像からテキスト抽出（OCR）"""
        prompt = """
        この画像からテキストを抽出してください。
        
        要件：
        - 全てのテキストを正確に読み取り
        - レイアウト情報も保持
        - 日本語・英語・数字を適切に認識
        - 表形式の場合は構造を保持
        
        結果をJSON形式で返してください：
        {
            "extracted_text": "抽出されたテキスト",
            "layout_info": "レイアウト情報",
            "confidence": "信頼度（0-1）",
            "detected_languages": ["ja", "en"]
        }
        """
        
        return self.analyze_image(image_path, prompt)
    
    def analyze_business_document(self, image_path: str) -> Dict[str, Any]:
        """ビジネス文書分析"""
        prompt = """
        このビジネス文書を分析して、以下の情報を抽出してください：
        
        {
            "document_type": "請求書/見積書/契約書/その他",
            "company_info": {
                "name": "会社名",
                "address": "住所",
                "contact": "連絡先"
            },
            "financial_info": {
                "amounts": ["金額リスト"],
                "total": "合計金額",
                "tax": "税額",
                "currency": "通貨"
            },
            "dates": {
                "issue_date": "発行日",
                "due_date": "支払期限",
                "delivery_date": "納期"
            },
            "items": [
                {
                    "name": "商品名",
                    "quantity": "数量",
                    "unit_price": "単価",
                    "amount": "金額"
                }
            ],
            "key_terms": ["重要条項"],
            "action_required": "必要なアクション"
        }
        """
        
        return self.analyze_image(image_path, prompt)
    
    def generate_business_content(self, content_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """ビジネス文書生成"""
        prompts = {
            "invoice_description": f"""
                以下の貸出データから、丁寧で分かりやすい請求書説明文を生成してください：
                
                取引先：{data.get('customer_name', '')}
                貸出期間：{data.get('period', '')}
                商品詳細：{data.get('items', [])}
                合計金額：{data.get('total_amount', 0)}
                
                要件：
                - 敬語使用
                - 100文字以内
                - ビジネス文書として適切
                - 明確で理解しやすい表現
            """,
            
            "sales_analysis": f"""
                以下の売上データを分析して、ビジネス洞察を提供してください：
                
                売上データ：{data.get('sales_data', {})}
                期間：{data.get('period', '')}
                
                分析項目：
                - トレンド分析
                - 成長機会の特定
                - リスク要因
                - 改善提案
                - 具体的なアクションプラン
                
                結果をJSON形式で構造化して返してください。
            """,
            
            "customer_recommendation": f"""
                以下の顧客データに基づいて、商品推奨を生成してください：
                
                顧客情報：{data.get('customer_info', {})}
                購入履歴：{data.get('purchase_history', [])}
                
                要求：
                - 3つの推奨商品
                - 推奨理由
                - 期待効果
                - 提案タイミング
            """
        }
        
        prompt = prompts.get(content_type, f"以下のデータについて分析してください：{data}")
        return self.generate_content(prompt)
    
    def analyze_csv_data(self, csv_content: str, analysis_type: str = "general") -> Dict[str, Any]:
        """CSVデータ分析"""
        prompt = f"""
        以下のCSVデータを分析してください：
        
        {csv_content}
        
        分析タイプ：{analysis_type}
        
        以下の観点から分析してください：
        1. データの概要と特徴
        2. トレンドやパターンの識別
        3. 異常値や注目すべき点
        4. ビジネス上の洞察
        5. 改善提案
        6. 次のアクション項目
        
        結果をJSON形式で構造化して返してください：
        {{
            "summary": "データ概要",
            "trends": ["発見されたトレンド"],
            "insights": ["ビジネス洞察"],
            "recommendations": ["改善提案"],
            "actions": ["推奨アクション"],
            "visualizations": ["推奨グラフタイプ"]
        }}
        """
        
        return self.generate_content(prompt)
    
    def process_multimodal_query(self, text: str, files: List[str] = None) -> Dict[str, Any]:
        """マルチモーダルクエリ処理"""
        content = [text]
        
        if files:
            for file_path in files:
                try:
                    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                        image = PIL.Image.open(file_path)
                        content.append(image)
                    # 将来的に音声・動画ファイルも対応予定
                except Exception as e:
                    logger.error(f"ファイル読み込みエラー {file_path}: {e}")
        
        return self.generate_content(content)


class GeminiCostOptimizer:
    """Geminiコスト最適化クラス"""
    
    def __init__(self, gemini_client: GeminiClient, openai_client=None):
        self.gemini = gemini_client
        self.openai = openai_client
        self.settings = QSettings("BusinessSystem", "CostOptimizer")
        
        # コスト設定（USD per 1M tokens）
        self.gemini_cost = {
            "input": 0.10,
            "output": 0.30
        }
        self.openai_cost = {
            "input": 5.00,  # GPT-4の概算
            "output": 15.00
        }
    
    def choose_optimal_ai(self, task_type: str, content_size: int) -> str:
        """最適なAIサービス選択"""
        # Geminiが得意なタスク
        gemini_preferred = [
            "image_analysis",
            "large_document",
            "data_analysis",
            "multimodal",
            "long_context"
        ]
        
        # 無料枠チェック
        if self.gemini.check_usage_limit() and task_type in gemini_preferred:
            return "gemini"
        
        # コスト比較
        if content_size > 100000:  # 大容量データ
            return "gemini"  # Geminiの方がコスト効率が良い
        
        return "openai" if self.openai else "gemini"
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """使用量統計取得"""
        return {
            "gemini": {
                "monthly_usage": self.gemini.monthly_token_usage,
                "remaining_free": self.gemini.monthly_limit - self.gemini.monthly_token_usage,
                "estimated_cost": 0.0  # 無料枠内
            },
            "openai": {
                "estimated_monthly_cost": 0.0  # 実装時に追加
            }
        }


# グローバルGeminiクライアント
gemini_client = GeminiClient()
cost_optimizer = GeminiCostOptimizer(gemini_client)