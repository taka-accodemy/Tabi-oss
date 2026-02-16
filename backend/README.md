# Chat BI Backend

Cube.js + LLM統合によるChatBIシステムのバックエンド実装です。

## 機能

- 自然言語クエリの処理とCube.jsクエリへの変換
- OpenAI GPT-4およびAnthropic Claude対応
- RESTful API エンドポイント
- JWT認証・認可
- リアルタイムデータ分析
- 高パフォーマンスキャッシング

## 技術スタック

- **Web Framework**: FastAPI
- **BI Engine**: Cube.js
- **LLM**: OpenAI GPT-4, Anthropic Claude
- **Database**: PostgreSQL
- **Cache**: Redis
- **Container**: Docker

## セットアップ

### 1. 依存関係のインストール

```bash
cd backend
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
cp .env.example .env
# .envファイルを編集して適切な値を設定
```

### 3. データベースの準備

```bash
# PostgreSQLを起動
docker run -d --name postgres \
  -e POSTGRES_DB=chatbi \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:15

# Redisを起動
docker run -d --name redis \
  -p 6379:6379 \
  redis:7
```

### 4. Cube.jsの起動

```bash
# Cube.jsサーバーを起動
npx cubejs-server

# または Docker Composeを使用
docker-compose up cube
```

### 5. バックエンドサーバーの起動

```bash
# 開発モード
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# または Docker
docker build -t chatbi-backend .
docker run -p 8000:8000 chatbi-backend
```

## API エンドポイント

### 認証
- `POST /api/v1/auth/token` - ログイン
- `POST /api/v1/auth/register` - ユーザー登録
- `GET /api/v1/auth/me` - 現在のユーザー情報

### クエリ
- `POST /api/v1/query/natural` - 自然言語クエリ
- `POST /api/v1/query/direct` - 直接Cube.jsクエリ
- `POST /api/v1/query/validate` - クエリ検証
- `GET /api/v1/query/suggestions` - クエリ提案

### スキーマ
- `GET /api/v1/schema` - スキーマ情報
- `GET /api/v1/schema/measures` - メジャー一覧
- `GET /api/v1/schema/dimensions` - ディメンション一覧
- `GET /api/v1/schema/search` - スキーマ検索

### ヘルスチェック
- `GET /api/v1/health` - 基本ヘルスチェック
- `GET /api/v1/health/detailed` - 詳細ヘルスチェック

## 使用方法

### 1. 認証

まず、ユーザーとしてログインします：

```bash
# ユーザー登録
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "password123"
  }'

# ログイン
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

レスポンス：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. 自然言語クエリの実行

取得したトークンを使用して自然言語クエリを実行：

```bash
# 自然言語クエリの例
curl -X POST "http://localhost:8000/api/v1/query/natural" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "今月の売上合計を教えて",
    "llm_provider": "openai"
  }'
```

レスポンス：
```json
{
  "success": true,
  "data": [
    {
      "Sales.totalAmount": 125000,
      "Sales.orderDate": "2024-01-01T00:00:00.000Z"
    }
  ],
  "cube_query": {
    "measures": ["Sales.totalAmount"],
    "timeDimensions": [
      {
        "dimension": "Sales.orderDate",
        "granularity": "month",
        "dateRange": "this month"
      }
    ]
  },
  "explanation": "今月の売上合計は125,000円です。",
  "visualization_suggestion": "bar",
  "confidence": 0.95
}
```

### 3. 複雑なクエリの例

```bash
# 商品カテゴリ別の売上分析
curl -X POST "http://localhost:8000/api/v1/query/natural" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "過去3ヶ月の商品カテゴリ別売上を月別で見せて",
    "conversation_history": [
      {
        "role": "user",
        "content": "前回の売上データを確認したい"
      }
    ]
  }'

# 顧客分析
curl -X POST "http://localhost:8000/api/v1/query/natural" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "最も売上の高い顧客TOP10を教えて",
    "context": {
      "focus": "customer_analysis",
      "period": "year"
    }
  }'
```

### 4. 直接Cube.jsクエリの実行

より詳細な制御が必要な場合：

```bash
curl -X POST "http://localhost:8000/api/v1/query/direct" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["Sales.totalAmount", "Sales.count"],
      "dimensions": ["Products.category"],
      "timeDimensions": [
        {
          "dimension": "Sales.orderDate",
          "granularity": "month",
          "dateRange": ["2024-01-01", "2024-03-31"]
        }
      ],
      "order": [
        ["Sales.totalAmount", "desc"]
      ]
    },
    "explain": true
  }'
```

### 5. スキーマ情報の取得

```bash
# 全スキーマ情報
curl -X GET "http://localhost:8000/api/v1/schema" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# メジャー一覧
curl -X GET "http://localhost:8000/api/v1/schema/measures" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# スキーマ検索
curl -X GET "http://localhost:8000/api/v1/schema/search?q=売上" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 6. クエリ支援機能

```bash
# クエリ提案
curl -X GET "http://localhost:8000/api/v1/query/suggestions?q=売上" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# クエリ検証
curl -X POST "http://localhost:8000/api/v1/query/validate" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "measures": ["Sales.totalAmount"],
    "dimensions": ["Products.category"]
  }'
```

### 7. Python クライアントの例

```python
import requests
import json

class ChatBIClient:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}" if token else None
        }
    
    def login(self, username, password):
        """ログイン"""
        response = requests.post(
            f"{self.base_url}/api/v1/auth/token",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        data = response.json()
        self.token = data["access_token"]
        self.headers["Authorization"] = f"Bearer {self.token}"
        return data
    
    def query_natural(self, query, llm_provider="openai", context=None):
        """自然言語クエリ"""
        payload = {
            "query": query,
            "llm_provider": llm_provider,
            "context": context or {}
        }
        response = requests.post(
            f"{self.base_url}/api/v1/query/natural",
            json=payload,
            headers=self.headers
        )
        return response.json()
    
    def get_schema(self):
        """スキーマ情報取得"""
        response = requests.get(
            f"{self.base_url}/api/v1/schema",
            headers=self.headers
        )
        return response.json()

# 使用例
client = ChatBIClient()
client.login("testuser", "password123")

# 自然言語クエリ
result = client.query_natural("今月の売上合計を教えて")
print(json.dumps(result, indent=2, ensure_ascii=False))

# スキーマ情報
schema = client.get_schema()
print(f"利用可能なメジャー数: {len(schema['measures'])}")
```

### 8. JavaScript クライアントの例

```javascript
class ChatBIClient {
    constructor(baseUrl = 'http://localhost:8000', token = null) {
        this.baseUrl = baseUrl;
        this.token = token;
    }
    
    async login(username, password) {
        const response = await fetch(`${this.baseUrl}/api/v1/auth/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `username=${username}&password=${password}`
        });
        const data = await response.json();
        this.token = data.access_token;
        return data;
    }
    
    async queryNatural(query, llmProvider = 'openai', context = {}) {
        const response = await fetch(`${this.baseUrl}/api/v1/query/natural`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({
                query: query,
                llm_provider: llmProvider,
                context: context
            })
        });
        return await response.json();
    }
    
    async getSchema() {
        const response = await fetch(`${this.baseUrl}/api/v1/schema`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });
        return await response.json();
    }
}

// 使用例
const client = new ChatBIClient();
await client.login('testuser', 'password123');

const result = await client.queryNatural('今月の売上合計を教えて');
console.log(result);
```

### 9. エラーハンドリング

```python
def handle_query_with_retry(client, query, max_retries=3):
    """エラー時の再試行処理"""
    for attempt in range(max_retries):
        try:
            result = client.query_natural(query)
            
            if not result['success']:
                print(f"クエリエラー: {result.get('error', 'Unknown error')}")
                continue
            
            if result.get('requires_clarification'):
                print(f"確認が必要: {result['clarification_question']}")
                # ユーザーからの追加情報を取得
                additional_info = input("追加情報を入力してください: ")
                query = f"{query}。{additional_info}"
                continue
            
            return result
            
        except Exception as e:
            print(f"リクエストエラー (試行 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise
    
    raise Exception("最大再試行回数に達しました")
```

### 10. ベストプラクティス

1. **認証トークンの管理**
   - トークンの有効期限を確認
   - 期限切れ前の自動更新

2. **クエリの最適化**
   - 明確で具体的な質問を使用
   - 文脈情報を適切に提供

3. **エラー処理**
   - 段階的フォールバック戦略
   - ユーザーフレンドリーなエラーメッセージ

4. **パフォーマンス**
   - 適切なページネーション
   - キャッシュの活用

## 設定

### 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `DATABASE_URL` | PostgreSQL接続URL | `postgresql://user:password@localhost/chatbi` |
| `REDIS_URL` | Redis接続URL | `redis://localhost:6379` |
| `OPENAI_API_KEY` | OpenAI APIキー | なし |
| `ANTHROPIC_API_KEY` | Anthropic APIキー | なし |
| `CUBE_API_URL` | Cube.js API URL | `http://localhost:4000` |
| `SECRET_KEY` | JWT秘密鍵 | ランダム文字列 |

### Cube.jsスキーマ

`cube_schemas/` ディレクトリに以下のスキーマが定義されています：

- `Sales.js` - 売上データ
- `Products.js` - 商品データ
- `Customers.js` - 顧客データ

## 開発

### テスト実行

```bash
# 単体テスト
pytest tests/

# カバレッジ付きテスト
pytest --cov=app tests/
```

### コード品質チェック

```bash
# リント
flake8 app/

# 型チェック
mypy app/

# フォーマット
black app/
```

## デプロイ

### Docker Compose

```bash
docker-compose up -d
```

### Kubernetes

```bash
# Helm chart を使用
helm install chatbi-backend ./charts/backend
```

## 監視

### メトリクス

- レスポンス時間
- エラー率
- アクティブユーザー数
- クエリ実行数

### ログ

- 構造化ログ（JSON形式）
- ログレベル：ERROR, WARN, INFO, DEBUG
- 外部ログ集約システム対応

## セキュリティ

- JWT認証
- CORS設定
- レート制限
- 入力検証
- SQLインジェクション対策

## パフォーマンス

- 非同期処理
- 接続プーリング
- クエリキャッシング
- 事前集計活用

## トラブルシューティング

### よくある問題

1. **データベース接続エラー**
   - 環境変数の確認
   - データベースの起動状態確認

2. **LLM API エラー**
   - APIキーの確認
   - レート制限の確認

3. **Cube.js接続エラー**
   - Cube.jsサーバーの起動確認
   - スキーマの構文確認

### ログの確認

```bash
# アプリケーションログ
docker logs chatbi-backend

# Cube.jsログ
docker logs chatbi-cube
```

## 今後の拡張

- [ ] WebSocket対応
- [ ] 機械学習モデル統合
- [ ] マルチテナント対応
- [ ] 高可用性構成
- [ ] 国際化対応