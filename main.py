#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
業務支援システム v3.0 メインエントリーポイント
PyQt6 ベースのモダンな業務管理システム
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QFont
import traceback

from core.app import create_app
from ui.main_window import MainWindow


class SplashScreen(QSplashScreen):
    """スプラッシュスクリーン"""
    
    def __init__(self):
        # 簡単なスプラッシュ画像を作成（実際のアプリでは画像ファイルを使用）
        pixmap = QPixmap(400, 200)
        pixmap.fill(Qt.GlobalColor.white)
        
        super().__init__(pixmap)
        
        # テキスト表示
        font = QFont("Yu Gothic UI", 16, QFont.Weight.Bold)
        self.setFont(font)
        
        self.showMessage(
            "業務支援システム v3.0\n\n初期化中...",
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            Qt.GlobalColor.black
        )


def check_requirements():
    """必要な要件をチェック"""
    try:
        import PyQt6
        import sqlalchemy
        import pandas
        print("OK 必要なライブラリが揃っています")
        return True
    except ImportError as e:
        print(f"NG 必要なライブラリが不足しています: {e}")
        return False


def show_error_dialog(title: str, message: str):
    """エラーダイアログ表示"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


def main():
    """メイン関数"""
    try:
        # 要件チェック
        if not check_requirements():
            show_error_dialog(
                "起動エラー",
                "必要なライブラリがインストールされていません。\n\n"
                "以下のコマンドを実行してください:\n"
                "pip install -r requirements_pyqt.txt"
            )
            return 1
        
        print("業務支援システム v3.0 を起動中...")
        
        # アプリケーション作成
        app = create_app()
        app.setQuitOnLastWindowClosed(True)
        
        # スプラッシュスクリーン表示
        splash = SplashScreen()
        splash.show()
        
        # イベントループを少し回す
        app.processEvents()
        
        # 初期化処理
        splash.showMessage(
            "業務支援システム v3.0\n\nUI初期化中...",
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            Qt.GlobalColor.black
        )
        app.processEvents()
        
        # メインウィンドウ作成
        main_window = MainWindow()
        app.set_main_window(main_window)
        
        # ダッシュボードのシグナル接続
        dashboard_widget = None
        for i in range(main_window.main_area.count()):
            widget = main_window.main_area.widget(i)
            if hasattr(widget, 'module_requested'):
                widget.module_requested.connect(main_window.open_module)
                dashboard_widget = widget
                break
        
        splash.showMessage(
            "業務支援システム v3.0\n\n準備完了",
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            Qt.GlobalColor.black
        )
        app.processEvents()
        
        # スプラッシュを閉じてメインウィンドウ表示
        QTimer.singleShot(1000, splash.close)
        QTimer.singleShot(1200, main_window.show)
        
        print("システムが正常に起動しました")
        print(f"データベース: {app.get_app_info()['database_path']}")
        print(f"設定ディレクトリ: {app.get_app_info()['config_dir']}")
        print("ヘルプ: メニューバーの「ヘルプ」→「使い方」を参照")
        print("設定: Ctrl+T でテーマ切り替え可能")
        
        # メインループ開始
        exit_code = app.exec()
        
        print("アプリケーションを終了しました")
        return exit_code
        
    except Exception as e:
        error_msg = f"起動エラーが発生しました:\n\n{str(e)}\n\n詳細:\n{traceback.format_exc()}"
        print(f"エラー: {error_msg}")
        
        show_error_dialog("起動エラー", error_msg)
        return 1


if __name__ == "__main__":
    # 作業ディレクトリをスクリプトのディレクトリに設定
    os.chdir(project_root)
    
    # メイン関数実行
    exit_code = main()
    sys.exit(exit_code)