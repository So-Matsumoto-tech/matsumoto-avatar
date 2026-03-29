# 松本壮 AI アバター

Claude API + ElevenLabs + D-ID を連携した AI アバター Web アプリ。

## 構成

```
matsumoto-avatar/
├── backend/
│   ├── main.py          # FastAPI サーバー
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html       # チャット UI
├── render.yaml          # Render デプロイ設定
└── README.md
```

## セットアップ手順

### 1. APIキーの取得

| サービス | 取得先 | 用途 |
|---------|--------|------|
| Anthropic | https://console.anthropic.com | 松本壮として返答 |
| ElevenLabs | https://elevenlabs.io | テキスト→音声変換 |
| D-ID | https://studio.d-id.com | 音声→口パク動画 |

### 2. D-ID の設定
1. D-ID ダッシュボードでアバター画像（松本壮の顔写真など）をアップロード
2. 発行された画像 URL を `DID_PRESENTER_ID` に設定
3. API Key を Base64 エンコードして `DID_API_KEY` に設定
   ```bash
   echo -n "your_email@example.com:your_did_api_key" | base64
   ```

### 3. ElevenLabs の声クローン（任意）
1. ElevenLabs の「Voice Lab」で声のサンプル音声をアップロード
2. 生成された Voice ID を `ELEVENLABS_VOICE_ID` に設定

### 4. ローカル動作確認
```bash
cd matsumoto-avatar
cp backend/.env.example backend/.env
# .env に各APIキーを記入

pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
# → http://localhost:8000 で確認
```

### 5. Render へデプロイ
1. GitHub にリポジトリを push
2. https://render.com で「New Web Service」→ GitHub リポジトリを選択
3. 環境変数（.env の内容）を Render のダッシュボードで設定
4. デプロイ実行

## API エンドポイント

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/chat` | POST | Claude API に質問→テキスト返答 |
| `/api/tts` | POST | テキスト→音声（ElevenLabs） |
| `/api/avatar` | POST | 音声URL→口パク動画（D-ID） |
| `/api/speak` | POST | chat + tts を一括実行（フロントはここを呼ぶ） |

## 今後の拡張

- D-ID Streaming API 対応（リアルタイム口パク）
- 会話履歴の保持（マルチターン対応）
- 声クローンの精度向上
