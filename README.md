# 業務支援システム v4.0 AI Enhanced

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

AI機能を搭載した包括的な業務管理システム。PyQt6ベースのモダンなデスクトップアプリケーションです。

## ✨ 主な機能

### 📊 業務管理
- **取引先管理**: 顧客情報の登録・編集・検索
- **商品管理**: 在庫管理、価格設定、カテゴリ分類
- **貸出管理**: レンタル・リース業務の追跡
- **請求書管理**: 自動計算、PDF出力対応
- **分析ダッシュボード**: 売上分析、在庫状況の可視化

### 🤖 AI機能
- **OpenAI API統合**: GPT-4による高度な文書解析
- **Gemini API統合**: Google Geminiによるデータ処理
- **音声認識**: マイクからの音声入力対応
- **音声合成**: テキストの読み上げ機能
- **Windows音声入力**: Win+Hショートカット連携

### 🎨 ユーザーインターフェース
- **モダンなデザイン**: ライト・ダークテーマ対応
- **レスポンシブレイアウト**: 画面サイズに応じた最適化
- **アクセシビリティ**: フォントサイズ調整、ハイコントラスト対応
- **多言語対応**: 日本語・英語サポート

## 🚀 クイックスタート

### システム要件
- **OS**: Windows 10/11 (推奨), Linux/WSL
- **Python**: 3.8以上
- **メモリ**: 4GB以上
- **ストレージ**: 500MB以上の空き容量

### インストール

1. **リポジトリのクローン**
```bash
git clone https://github.com/yourusername/business-system-v40.git
cd business-system-v40
```

2. **仮想環境の作成**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **依存関係のインストール**
```bash
pip install -r requirements.txt
```

4. **アプリケーションの起動**
```bash
# Windows (推奨)
start_app.bat

# または直接起動
python main.py
```

### 初期設定

1. **AI API設定** (オプション)
   - `config/ai_settings.env.example` を `config/ai_settings.env` にコピー
   - OpenAI API キーを設定
   - Gemini API キーを設定

2. **音声機能設定** (オプション)
   - Windows設定でマイクアクセスを許可
   - 音声認識ライブラリのインストール:
   ```bash
   pip install SpeechRecognition pyaudio
   ```

## 📖 使用方法

### 基本操作

1. **アプリケーション起動**
   ```bash
   python main.py
   ```

2. **新規データ登録**
   - 左サイドバーから該当メニューを選択
   - フォームに必要情報を入力
   - 保存ボタンをクリック

3. **データ検索・編集**
   - 一覧タブで対象データを検索
   - ダブルクリックで編集モードに移行

### 音声入力機能

- **Windows音声入力**: `Ctrl+H` またはボタンクリック
- **アプリ内音声認識**: `Ctrl+Shift+V`
- **テキスト入力**: フォールバック機能として利用可能

### ショートカットキー

- `Ctrl+N`: 新規作成
- `Ctrl+S`: 保存
- `Ctrl+F`: 検索
- `Ctrl+T`: テーマ切り替え
- `Ctrl+H`: Windows音声入力
- `F1`: ヘルプ

## 🛠️ 開発

### プロジェクト構造

```
business_system_v40_gemini/ai_enhanced_version/
├── main.py                 # メインエントリーポイント
├── core/                   # コアシステム
│   ├── app.py             # アプリケーション管理
│   ├── database.py        # データベース操作
│   ├── ai_integration.py  # AI API統合
│   └── config_manager.py  # 設定管理
├── ui/                    # ユーザーインターフェース
│   ├── main_window.py     # メインウィンドウ
│   ├── components/        # UI コンポーネント
│   └── themes/           # テーマファイル
├── modules/              # 業務モジュール
│   ├── customers.py      # 取引先管理
│   ├── products.py       # 商品管理
│   ├── loans.py          # 貸出管理
│   └── analytics.py      # 分析機能
├── config/               # 設定ファイル
├── docs/                 # ドキュメント
└── tests/               # テスト
```

### 開発環境セットアップ

1. **開発用依存関係のインストール**
```bash
pip install -r requirements-dev.txt
```

2. **コード品質チェック**
```bash
# Linting
flake8 .

# Type checking
mypy .
```

3. **テスト実行**
```bash
pytest tests/
```

### ビルド

```bash
# 実行可能ファイル作成
python build_app.py

# インストーラー作成 (Windows)
python create_installer.py
```

## 🔧 診断・トラブルシューティング

### 診断ツール

```bash
# システム診断
python startup_diagnostic.py

# WSL環境診断
python headless_diagnostic.py
```

### よくある問題

1. **アプリが起動しない**
   - Python 3.8以上がインストールされているか確認
   - 必須ライブラリがインストールされているか確認
   - `start_app.bat` を使用して起動

2. **音声入力が動作しない**
   - Windows: プライバシー設定でマイクアクセスを許可
   - `SpeechRecognition`、`pyaudio` ライブラリをインストール

3. **データベースエラー**
   - `business_system.db` ファイルの権限を確認
   - バックアップからの復元を実行

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 🤝 コントリビューション

プルリクエストや課題報告を歓迎します。

1. フォークを作成
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📞 サポート

- 📧 Email: support@example.com
- 📖 Documentation: [docs/](docs/)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/business-system-v40/issues)

## 🔄 更新履歴

### v4.0.0 (2025-06-14)
- AI機能の統合 (OpenAI, Gemini)
- Windows音声入力サポート
- UI/UX大幅改善
- 包括的なエラーハンドリング
- 診断ツールの追加

### v3.0.0
- PyQt6への移行
- モジュラー設計の採用
- テーマシステムの実装

---

**開発者**: Claude Code  
**最終更新**: 2025-06-14