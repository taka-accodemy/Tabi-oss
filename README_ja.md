# Tabi - ChatBI: Cube.js + LLM 統合プラットフォーム

Tabiへようこそ。自然言語でデータ分析を行うためのChatBIプラットフォームです。Cube.jsのセマンティックレイヤーと大規模言語モデル（LLM）を組み合わせ、直感的なデータ分析を提供します。

## 🚀 概要

Tabiは、非エンジニアでも自然言語のクエリを通じて複雑なデータ分析を行えるようにします。以下の技術を統合しています：

- **Cube.js** - セマンティックレイヤーとクエリの最適化
- **LLM 統合** - OpenAI GPT-4 および Anthropic Claude
- **FastAPI バックエンド** - クエリ処理のためのRESTful API
- **React フロントエンド** - Tailwind CSS + Shadcn UI を使用したモダンなチャットインターフェース
- **マルチDB対応** - PostgreSQL / BigQuery / AWS Iceberg (Athena)
- **Redis** - キャッシングとセッション管理

## 📊 テスト環境

UCI Online Retail データセットを使用したプリセット環境が用意されています：

- **397,884** 件の販売トランザクション
- **37** カ国の **4,338** 人の顧客
- **3,877** 種類の商品
- **総売上**: £8,911,407.90

## 🛠 クイックスタート

### 前提条件

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (ローカルでのフロントエンド開発用)

### 1. クローンとセットアップ

```bash
git clone <repository-url>
cd Tabi
```

### 2. 環境変数の設定

テンプレートから `.env` ファイルを作成します：

```bash
cp .env.template .env
```

`.env` を編集して API キーを追加してください：

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

### 3. サービスの起動 (Docker)

```bash
# 全てのサービスを起動
docker-compose up -d
```

以下のURLでアクセス可能になります：

- **フロントエンド**: `http://localhost:5173`
- **バックエンド API**: `http://localhost:8000`
- **Cube.js**: `http://localhost:4000`

### 4. テストデータのロード

```bash
# UCI Online Retail データセットを Postgres にロード
python3 scripts/etl_to_postgres.py
```

## 🎯 使い方

### データベース接続設定

UIの **Settings** (設定) -> **データベース接続** からデータソースを設定できます。以下のDBをサポートしています：

- **PostgreSQL**: 標準的なリレーショナルデータベース。
- **GCP BigQuery**: JSONキー認証によるクラウドデータウェアハウス。
- **AWS Iceberg**: Athena経由のデータレイク。

## 🏗 アーキテクチャ

```
[React Frontend] → [FastAPI Backend] → [Cube.js] → [Target Database]
       ↓                  ↓               ↓              ↓
   [Shadcn UI]       [LLM Bridge]     [Semantic]    [PG/BQ/Iceberg]
```

## 📁 プロジェクト構成

```
Tabi/
├── backend/              # FastAPI アプリケーション
├── frontend-react/       # React (Vite) アプリケーション
├── cubejs/              # Cube.js 設定
├── database/            # データベース初期化
├── scripts/             # データ処理スクリプト
├── deprecated/          # 以前の Streamlit コードやスクリプト
├── docker-compose.yml   # Docker Compose 設定
└── COPYING              # ライセンス情報
```

## 🔧 開発

### バックエンド

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### フロントエンド

```bash
cd frontend-react
npm install
npm run dev
```

## 📄 ライセンス

このプロジェクトは **GNU Lesser General Public License v3.0 (LGPLv3)** の下でライセンスされています。詳細は [COPYING](COPYING) および [COPYING.LESSER](COPYING.LESSER) を参照してください。

## 🤝 貢献

1. リポジトリをフォークする
2. フィーチャーブランチを作成する: `git checkout -b feature/new-feature`
3. 変更をコミットする: `git commit -am 'Add new feature'`
4. ブランチをプッシュする: `git push origin feature/new-feature`
5. プルリクエストを作成する

## 🙏 謝辞

- UCI Machine Learning Repository (Online Retail データセット)
- Cube.js チーム (セマンティックレイヤーフレームワーク)
- OpenAI & Anthropic (LLM 機能)
- オープンソースコミュニティの皆様

---

**Happy Data Journey! 🚀**
