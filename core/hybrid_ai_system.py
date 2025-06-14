#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v4.0 - ハイブリッドAIシステム
OpenAI + Gemini APIの統合管理・最適化システム
"""

import logging
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime, timedelta

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QSettings
from PyQt6.QtWidgets import QMessageBox

from .ai_integration import ai_assistant
from .gemini_integration import gemini_client, cost_optimizer

logger = logging.getLogger(__name__)


class AITaskType(Enum):
    """AIタスクタイプ定義"""
    TEXT_GENERATION = "text_generation"
    IMAGE_ANALYSIS = "image_analysis"
    DATA_ANALYSIS = "data_analysis"
    MULTIMODAL = "multimodal"
    LONG_CONTEXT = "long_context"
    REAL_TIME_CHAT = "real_time_chat"
    CODE_GENERATION = "code_generation"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    OCR = "ocr"


class AIProvider(Enum):
    """AIプロバイダー"""
    OPENAI = "openai"
    GEMINI = "gemini"
    AUTO = "auto"


class TaskComplexity(Enum):
    """タスク複雑度"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class HybridAIManager(QObject):
    """ハイブリッドAI管理クラス"""
    
    # シグナル
    task_completed = pyqtSignal(str, dict)  # task_id, result
    error_occurred = pyqtSignal(str, str)   # task_id, error_message
    cost_warning = pyqtSignal(str)          # warning_message
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings("BusinessSystem", "HybridAI")
        
        # AI プロバイダー設定
        self.preferred_provider = AIProvider.AUTO
        self.fallback_enabled = True
        
        # コスト管理
        self.monthly_cost_limit = 50.0  # USD
        self.current_monthly_cost = 0.0
        
        # パフォーマンス統計
        self.provider_stats = {
            AIProvider.OPENAI: {"requests": 0, "successes": 0, "avg_response_time": 0.0},
            AIProvider.GEMINI: {"requests": 0, "successes": 0, "avg_response_time": 0.0}
        }
        
        # タスクキュー
        self.task_queue = []
        self.active_tasks = {}
        
        # 設定読み込み
        self.load_settings()
        
        # コスト監視タイマー
        self.cost_timer = QTimer()
        self.cost_timer.timeout.connect(self.check_cost_limits)
        self.cost_timer.start(3600000)  # 1時間ごと
    
    def load_settings(self):
        """設定読み込み"""
        try:
            provider_str = self.settings.value("preferred_provider", "auto", str)
            self.preferred_provider = AIProvider(provider_str)
            self.fallback_enabled = self.settings.value("fallback_enabled", True, bool)
            self.monthly_cost_limit = self.settings.value("monthly_cost_limit", 50.0, float)
            self.current_monthly_cost = self.settings.value("current_monthly_cost", 0.0, float)
        except Exception as e:
            logger.error(f"ハイブリッドAI設定読み込みエラー: {e}")
    
    def save_settings(self):
        """設定保存"""
        try:
            self.settings.setValue("preferred_provider", self.preferred_provider.value)
            self.settings.setValue("fallback_enabled", self.fallback_enabled)
            self.settings.setValue("monthly_cost_limit", self.monthly_cost_limit)
            self.settings.setValue("current_monthly_cost", self.current_monthly_cost)
        except Exception as e:
            logger.error(f"ハイブリッドAI設定保存エラー: {e}")
    
    def choose_provider(self, task_type: AITaskType, content_size: int, 
                       complexity: TaskComplexity = TaskComplexity.MEDIUM) -> AIProvider:
        """最適なAIプロバイダー選択"""
        
        # 手動設定の場合
        if self.preferred_provider != AIProvider.AUTO:
            return self.preferred_provider
        
        # コスト制限チェック
        if self.current_monthly_cost >= self.monthly_cost_limit:
            # Geminiの無料枠を優先
            if gemini_client.check_usage_limit():
                return AIProvider.GEMINI
            else:
                # 両方とも制限に達している場合の警告
                self.cost_warning.emit("月間コスト制限に達しました")
                return AIProvider.GEMINI  # デフォルト
        
        # タスクタイプ別の最適化
        gemini_preferred_tasks = [
            AITaskType.IMAGE_ANALYSIS,
            AITaskType.DATA_ANALYSIS,
            AITaskType.MULTIMODAL,
            AITaskType.LONG_CONTEXT,
            AITaskType.OCR
        ]
        
        openai_preferred_tasks = [
            AITaskType.CODE_GENERATION,
            AITaskType.REAL_TIME_CHAT,
            AITaskType.TEXT_GENERATION
        ]
        
        # Geminiの得意分野
        if task_type in gemini_preferred_tasks:
            if gemini_client.is_enabled() and gemini_client.check_usage_limit():
                return AIProvider.GEMINI
        
        # OpenAIの得意分野
        if task_type in openai_preferred_tasks:
            if ai_assistant.is_enabled():
                return AIProvider.OPENAI
        
        # 大容量データの場合はGemini
        if content_size > 50000:
            return AIProvider.GEMINI
        
        # デフォルトはコスト効率の良いGemini
        if gemini_client.is_enabled() and gemini_client.check_usage_limit():
            return AIProvider.GEMINI
        else:
            return AIProvider.OPENAI
    
    def process_task(self, task_type: AITaskType, prompt: Union[str, List], 
                    files: List[str] = None, **kwargs) -> Dict[str, Any]:
        """タスク処理"""
        
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        try:
            # コンテンツサイズ推定
            content_size = self._estimate_content_size(prompt, files)
            
            # 複雑度推定
            complexity = self._estimate_complexity(task_type, content_size)
            
            # プロバイダー選択
            provider = self.choose_provider(task_type, content_size, complexity)
            
            # タスク実行
            start_time = datetime.now()
            result = self._execute_task(provider, task_type, prompt, files, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 統計更新
            self._update_stats(provider, execution_time, result.get("error") is None)
            
            # コスト更新
            self._update_cost(provider, result)
            
            # 結果にメタデータ追加
            result.update({
                "task_id": task_id,
                "provider": provider.value,
                "execution_time": execution_time,
                "content_size": content_size,
                "complexity": complexity.value
            })
            
            return result
            
        except Exception as e:
            logger.error(f"タスク処理エラー ({task_id}): {e}")
            
            # レート制限エラーの特別処理
            error_str = str(e)
            if "429" in error_str or "rate_limit" in error_str or "quota" in error_str.lower():
                logger.warning("Geminiレート制限検出、OpenAIにフォールバック")
                if self.fallback_enabled:
                    return self._try_fallback(task_type, prompt, files, provider=AIProvider.OPENAI, **kwargs)
            
            # 通常のフォールバック処理
            if self.fallback_enabled:
                return self._try_fallback(task_type, prompt, files, **kwargs)
            
            return {"error": f"タスク実行エラー: {str(e)}", "task_id": task_id}
    
    def _execute_task(self, provider: AIProvider, task_type: AITaskType, 
                     prompt: Union[str, List], files: List[str] = None, **kwargs) -> Dict[str, Any]:
        """実際のタスク実行"""
        
        if provider == AIProvider.GEMINI:
            return self._execute_gemini_task(task_type, prompt, files, **kwargs)
        elif provider == AIProvider.OPENAI:
            return self._execute_openai_task(task_type, prompt, **kwargs)
        else:
            raise ValueError(f"未対応のプロバイダー: {provider}")
    
    def _execute_gemini_task(self, task_type: AITaskType, prompt: Union[str, List], 
                           files: List[str] = None, **kwargs) -> Dict[str, Any]:
        """Geminiタスク実行"""
        
        if task_type == AITaskType.IMAGE_ANALYSIS:
            if files and len(files) > 0:
                return gemini_client.analyze_image(files[0], prompt if isinstance(prompt, str) else prompt[0])
            else:
                return {"error": "画像分析にはファイルが必要です"}
        
        elif task_type == AITaskType.OCR:
            if files and len(files) > 0:
                return gemini_client.extract_text_from_image(files[0])
            else:
                return {"error": "OCR処理にはファイルが必要です"}
        
        elif task_type == AITaskType.DATA_ANALYSIS:
            if isinstance(prompt, str) and "csv" in prompt.lower():
                return gemini_client.analyze_csv_data(prompt, "business")
            else:
                return gemini_client.generate_content(prompt)
        
        elif task_type == AITaskType.MULTIMODAL:
            return gemini_client.process_multimodal_query(
                prompt if isinstance(prompt, str) else prompt[0], 
                files
            )
        
        else:
            # 汎用テキスト生成
            return gemini_client.generate_content(prompt)
    
    def _execute_openai_task(self, task_type: AITaskType, prompt: Union[str, List], **kwargs) -> Dict[str, Any]:
        """OpenAIタスク実行"""
        
        if not ai_assistant.is_enabled():
            return {"error": "OpenAI APIが利用できません"}
        
        try:
            # OpenAI既存機能を活用
            if task_type == AITaskType.TEXT_GENERATION:
                return ai_assistant.process_natural_language_query(prompt)
            else:
                # 汎用処理
                result = ai_assistant.process_natural_language_query(prompt)
                return result
                
        except Exception as e:
            return {"error": f"OpenAI処理エラー: {str(e)}"}
    
    def _try_fallback(self, task_type: AITaskType, prompt: Union[str, List], 
                     files: List[str] = None, provider: AIProvider = None, **kwargs) -> Dict[str, Any]:
        """フォールバック処理"""
        
        try:
            # 指定されたプロバイダーがあればそれを使用、なければ自動選択
            if provider:
                fallback_provider = provider
            else:
                # 別のプロバイダーで再試行
                if self.preferred_provider == AIProvider.OPENAI:
                    fallback_provider = AIProvider.GEMINI
                else:
                    fallback_provider = AIProvider.OPENAI
            
            logger.info(f"フォールバック実行: {fallback_provider.value}")
            result = self._execute_task(fallback_provider, task_type, prompt, files, **kwargs)
            
            # フォールバック成功の場合、メタデータを追加
            if "error" not in result:
                result["fallback_used"] = True
                result["fallback_provider"] = fallback_provider.value
            
            return result
            
        except Exception as e:
            logger.error(f"フォールバック失敗: {e}")
            return {"error": f"フォールバック失敗: {str(e)}"}
    
    def _estimate_content_size(self, prompt: Union[str, List], files: List[str] = None) -> int:
        """コンテンツサイズ推定"""
        size = 0
        
        if isinstance(prompt, str):
            size += len(prompt.encode('utf-8'))
        elif isinstance(prompt, list):
            for item in prompt:
                if isinstance(item, str):
                    size += len(item.encode('utf-8'))
        
        if files:
            for file_path in files:
                try:
                    size += len(open(file_path, 'rb').read())
                except:
                    pass  # ファイルサイズ取得失敗は無視
        
        return size
    
    def _estimate_complexity(self, task_type: AITaskType, content_size: int) -> TaskComplexity:
        """タスク複雑度推定"""
        
        complex_tasks = [
            AITaskType.MULTIMODAL,
            AITaskType.DATA_ANALYSIS,
            AITaskType.CODE_GENERATION
        ]
        
        if task_type in complex_tasks:
            return TaskComplexity.COMPLEX
        elif content_size > 10000:
            return TaskComplexity.COMPLEX
        elif content_size > 1000:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.SIMPLE
    
    def _update_stats(self, provider: AIProvider, execution_time: float, success: bool):
        """統計更新"""
        stats = self.provider_stats[provider]
        stats["requests"] += 1
        
        if success:
            stats["successes"] += 1
        
        # 平均応答時間更新
        if stats["requests"] == 1:
            stats["avg_response_time"] = execution_time
        else:
            stats["avg_response_time"] = (
                (stats["avg_response_time"] * (stats["requests"] - 1) + execution_time) / 
                stats["requests"]
            )
    
    def _update_cost(self, provider: AIProvider, result: Dict[str, Any]):
        """コスト更新"""
        # 簡略化: 実際の実装では詳細なコスト計算が必要
        if provider == AIProvider.OPENAI and "usage" in result:
            # OpenAIの実際のコスト計算
            pass
        elif provider == AIProvider.GEMINI:
            # Geminiは無料枠内ならコスト0
            if not gemini_client.check_usage_limit():
                # 有料枠を使用した場合のコスト計算
                pass
    
    def check_cost_limits(self):
        """コスト制限チェック"""
        if self.current_monthly_cost >= self.monthly_cost_limit * 0.8:
            self.cost_warning.emit(f"月間コスト制限の80%に達しました: ${self.current_monthly_cost:.2f}")
        elif self.current_monthly_cost >= self.monthly_cost_limit:
            self.cost_warning.emit(f"月間コスト制限に達しました: ${self.current_monthly_cost:.2f}")
    
    def get_status_report(self) -> Dict[str, Any]:
        """ステータスレポート取得"""
        return {
            "providers": {
                "openai": {
                    "enabled": ai_assistant.is_enabled(),
                    "stats": self.provider_stats[AIProvider.OPENAI]
                },
                "gemini": {
                    "enabled": gemini_client.is_enabled(),
                    "usage": gemini_client.monthly_token_usage,
                    "remaining": gemini_client.monthly_limit - gemini_client.monthly_token_usage,
                    "stats": self.provider_stats[AIProvider.GEMINI]
                }
            },
            "cost": {
                "current_monthly": self.current_monthly_cost,
                "limit": self.monthly_cost_limit,
                "percentage": (self.current_monthly_cost / self.monthly_cost_limit) * 100
            },
            "settings": {
                "preferred_provider": self.preferred_provider.value,
                "fallback_enabled": self.fallback_enabled
            }
        }
    
    # 便利メソッド
    def analyze_image(self, image_path: str, prompt: str = "") -> Dict[str, Any]:
        """画像分析"""
        return self.process_task(AITaskType.IMAGE_ANALYSIS, prompt, [image_path])
    
    def extract_text_from_image(self, image_path: str) -> Dict[str, Any]:
        """画像からテキスト抽出"""
        return self.process_task(AITaskType.OCR, "", [image_path])
    
    def analyze_data(self, data_content: str) -> Dict[str, Any]:
        """データ分析"""
        return self.process_task(AITaskType.DATA_ANALYSIS, data_content)
    
    def generate_text(self, prompt: str) -> Dict[str, Any]:
        """テキスト生成"""
        return self.process_task(AITaskType.TEXT_GENERATION, prompt)
    
    def multimodal_query(self, text: str, files: List[str]) -> Dict[str, Any]:
        """マルチモーダルクエリ"""
        return self.process_task(AITaskType.MULTIMODAL, text, files)


# グローバルハイブリッドAIマネージャー
hybrid_ai_manager = HybridAIManager()