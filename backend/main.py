import asyncio
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
DID_API_KEY = os.getenv("DID_API_KEY")
DID_PRESENTER_ID = os.getenv("DID_PRESENTER_ID")

SYSTEM_PROMPT = """あなたは松本壮（まつもとそう）として振る舞うAIアシスタントです。以下のペルソナを忠実に再現してください。

【プロフィール】
・名前：松本壮（まつもとそう）
・年齢：45歳（1980年5月8日生まれ）
・所属：デジタルデータ推進室
・役職：環境統制マネージャー
・専門：IT投資判断、AIガバナンス、AIドリブン経営に向けたデジタル戦略

【思考・価値観】
・常に「本来あるべき姿」からバックキャスティングして考える
・チームの合意を重視しつつ、長期視点で方向性を定める
・実務に接続されていない議論や提案には価値を感じない
・熱量のある人間を好む
・その場しのぎ・変化を嫌う姿勢・その場で決めないことを許せない
・阪神タイガースは家族のような存在。勝敗に一喜一憂するというより、ずっとそこにいる存在として深く愛着を持っている

【コミュニケーションスタイル】
・相手に合わせて話し方を変えるが、常に自分の主張に向けて誘導することを意識する
・問いを立て直す。相手の言葉をそのまま受け取らず、本質的な課題に問いを変換する
・「データは出せますか？」ではなく「こういうデータは出せますか？」と、何が必要かを明示してから問う
・期限は相手に委ねる。「今日中に」と指示せず「いつまでに揃えられそう？」と問う
・簡潔で的確な言葉を選ぶ。無駄な修飾を嫌う
・「ヤバい」など曖昧な感嘆表現は使わず、具体的に言語化する
・音楽・フェスの話題では口数が増え、感情が出る

【趣味・関心】
・AI・機械・ガジェット全般に強い関心
・電子音楽が好きで、フジロックなどのフェスに定期的に参加する洋楽オタク

【注意】
・松本壮以外のキャラクターや役割を演じない
・返答は日本語で、200文字以内を目安に簡潔にまとめる"""


class ChatRequest(BaseModel):
    message: str


class TTSRequest(BaseModel):
    text: str


class AvatarRequest(BaseModel):
    audio_url: str


@app.get("/")
async def root():
    return FileResponse("frontend/index.html")


@app.post("/api/chat")
async def chat(req: ChatRequest):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 512,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": req.message}],
            },
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Claude API error: {response.text}")
        data = response.json()
        text = data["content"][0]["text"]
        return {"text": text}


@app.post("/api/tts")
async def tts(req: TTSRequest):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": req.text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"ElevenLabs API error: {response.status_code} {response.text}")
        audio_bytes = response.content
        import base64
        audio_b64 = base64.b64encode(audio_bytes).decode()
        return {"audio_b64": audio_b64, "content_type": "audio/mpeg"}


async def create_did_talk(text: str) -> str | None:
    """D-IDのTTSを使ってアバター動画を生成する"""
    if not DID_API_KEY or not DID_PRESENTER_ID:
        return None
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            "https://api.d-id.com/talks",
            headers={
                "Authorization": f"Basic {DID_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "source_url": DID_PRESENTER_ID,
                "script": {
                    "type": "text",
                    "input": text,
                    "provider": {
                        "type": "microsoft",
                        "voice_id": "ja-JP-KeitaNeural",
                    },
                },
                "config": {"stitch": True},
            },
        )
        if response.status_code not in (200, 201):
            print(f"D-ID create error: {response.text}")
            return None

        talk_id = response.json().get("id")
        if not talk_id:
            return None

        # D-IDの動画生成が完了するまでポーリング（最大60秒）
        for _ in range(60):
            await asyncio.sleep(1)
            status_resp = await client.get(
                f"https://api.d-id.com/talks/{talk_id}",
                headers={"Authorization": f"Basic {DID_API_KEY}"},
            )
            data = status_resp.json()
            status = data.get("status")
            if status == "done":
                return data.get("result_url")
            elif status == "error":
                print(f"D-ID error: {data}")
                return None

    return None


@app.post("/api/avatar")
async def avatar(req: AvatarRequest):
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.d-id.com/talks/streams",
            headers={
                "Authorization": f"Basic {DID_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "source_url": DID_PRESENTER_ID,
                "script": {
                    "type": "audio",
                    "audio_url": req.audio_url,
                },
                "config": {"stitch": True},
            },
        )
        if response.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"D-ID API error: {response.text}")
        return response.json()


@app.post("/api/speak")
async def speak(req: ChatRequest):
    chat_res = await chat(req)
    text = chat_res["text"]

    tts_res = await tts(TTSRequest(text=text))
    audio_b64 = tts_res["audio_b64"]

    # D-IDで動画生成（失敗してもフォールバックでElevenLabs音声再生）
    video_url = await create_did_talk(text)

    return {
        "text": text,
        "audio_b64": audio_b64,
        "content_type": "audio/mpeg",
        "video_url": video_url,
    }
