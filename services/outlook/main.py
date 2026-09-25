"""Outlook login + Rockstar OTP — same credential flow as wichxshop-webmain."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field

IDS_FILE = Path(__file__).parent / "ids.txt"
TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
DONGVAN_URL = "https://tools.dongvanfb.net/api/get_messages_oauth2"

OTP_REGEX = re.compile(
    r"\b(?!000000|111111|222222|333333|444444|555555|666666|777777|888888|999999)\d{6}\b"
)
ROCKSTAR_KEYWORDS = (
    "verification code",
    "verify",
    "security code",
    "authentication code",
    "your rockstar games",
    "código de verificação",
    "código de verificación",
    "code de vérification",
    "bestätigungscode",
    "код подтверждения",
    "código",
    "codigo",
    "code",
    "รหัสยืนยัน",
)
MAX_MINUTES = 30
MAX_EMAILS = 50


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    auth_mode: str = Field(default="password", pattern="^(password|oauth2)$")
    refresh_token: str | None = None
    client_id: str | None = None


class LoginResponse(BaseModel):
    success: bool


class PullCodeRequest(LoginRequest):
    pass


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_credentials() -> dict[str, tuple[str, str, str]]:
    credentials: dict[str, tuple[str, str, str]] = {}
    if not IDS_FILE.exists():
        return credentials

    for line in IDS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 4:
            continue
        email, password, client_id = parts[0], parts[1], parts[-1]
        refresh_token = "|".join(parts[2:-1]).strip()
        credentials[email.lower()] = (password, refresh_token, client_id)
    return credentials


def tokens_from_password(email: str, password: str) -> tuple[str, str]:
    stored = load_credentials()
    row = stored.get(email.lower())
    if row is None:
        raise HTTPException(status_code=404, detail="Email not found")
    stored_password, refresh_token, client_id = row
    if stored_password != password:
        raise HTTPException(status_code=401, detail="Invalid password")
    return refresh_token, client_id


def resolve_tokens(request: LoginRequest) -> tuple[str, str]:
    if request.auth_mode == "oauth2":
        refresh_token = (request.refresh_token or "").strip()
        client_id = (request.client_id or "").strip()
        if not refresh_token or not client_id:
            raise HTTPException(status_code=400, detail="กรุณาระบุ Refresh Token และ Client ID")
        return refresh_token, client_id
    return tokens_from_password(request.email, request.password)


def get_access_token(refresh_token: str, client_id: str) -> str:
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": "https://graph.microsoft.com/Mail.Read offline_access",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Token หมดอายุหรือไม่ถูกต้อง")
    return resp.json()["access_token"]


def strip_html(text: str) -> str:
    cleaned = re.sub(r"<[^>]*>", " ", text)
    cleaned = (
        cleaned.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def is_rockstar_mail(sender: str, subject: str, body: str) -> bool:
    haystack = f"{sender} {subject} {body}".lower()
    from_rockstar = (
        "rockstargames.com" in sender.lower()
        or "rockstar" in sender.lower()
        or "rockstar games" in haystack
    )
    if not from_rockstar:
        return False
    return any(keyword in haystack for keyword in ROCKSTAR_KEYWORDS) or bool(
        OTP_REGEX.search(haystack)
    )


def extract_otp(text: str, preferred: str | None = None) -> str | None:
    if preferred and OTP_REGEX.fullmatch(preferred):
        return preferred
    matches = OTP_REGEX.findall(strip_html(text))
    for code in matches:
        idx = text.lower().find(code)
        context = text.lower()[max(0, idx - 50) : idx + 50]
        if "example" not in context:
            return code
    return matches[0] if matches else None


def relative_time(received_at: datetime) -> str:
    delta = datetime.now(timezone.utc) - received_at
    minutes = max(0, int(delta.total_seconds() // 60))
    if minutes < 1:
        return "เมื่อสักครู่"
    if minutes < 60:
        return f"{minutes} นาทีที่แล้ว"
    hours = minutes // 60
    return f"{hours} ชั่วโมงที่แล้ว"


def fetch_graph_messages(access_token: str) -> list[dict]:
    resp = requests.get(
        f"{GRAPH_API_URL}/me/messages",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "$top": str(MAX_EMAILS),
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,bodyPreview,body,receivedDateTime,from",
        },
        timeout=20,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="ไม่สามารถดึงเมลจาก Microsoft ได้")
    return resp.json().get("value", [])


def parse_dongvan_date(value: str | None) -> datetime | None:
    if not value:
        return None
    native = datetime.fromisoformat(value.replace("Z", "+00:00")) if "T" in value else None
    if native is not None:
        return native if native.tzinfo else native.replace(tzinfo=timezone.utc)

    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    match = re.match(r"^(\d{1,2}):(\d{2})\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})$", value)
    if not match:
        return None
    hour, minute, day, month, year = map(int, match.groups())
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def fetch_dongvan_messages(email: str, refresh_token: str, client_id: str) -> list[dict]:
    resp = requests.post(
        DONGVAN_URL,
        json={
            "email": email,
            "refresh_token": refresh_token,
            "client_id": client_id,
            "list_mail": "all",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="ไม่สามารถดึงเมลจาก OAuth2 ได้")
    data = resp.json()
    if data.get("status") is False:
        raise HTTPException(status_code=401, detail=data.get("message") or "OAuth2 ไม่ถูกต้อง")
    return data.get("messages") or []


def collect_codes(
    *,
    email: str,
    auth_mode: str,
    refresh_token: str,
    client_id: str,
) -> list[dict]:
    threshold = datetime.now(timezone.utc) - timedelta(minutes=MAX_MINUTES)
    codes: list[dict] = []

    if auth_mode == "oauth2":
        try:
            access_token = get_access_token(refresh_token, client_id)
            messages = fetch_graph_messages(access_token)
            for msg in messages:
                sender = msg.get("from", {}).get("emailAddress", {}).get("address", "")
                subject = msg.get("subject") or ""
                body = f"{msg.get('body', {}).get('content', '')} {msg.get('bodyPreview', '')}"
                received_raw = msg.get("receivedDateTime")
                received_at = (
                    datetime.fromisoformat(received_raw.replace("Z", "+00:00"))
                    if received_raw
                    else None
                )
                if not received_at or received_at < threshold:
                    continue
                if not is_rockstar_mail(sender, subject, body):
                    continue
                code = extract_otp(body)
                if not code:
                    continue
                codes.append(
                    {
                        "code": code,
                        "time": relative_time(received_at),
                        "is_new": received_at >= datetime.now(timezone.utc) - timedelta(minutes=3),
                    }
                )
            return codes
        except HTTPException:
            messages = fetch_dongvan_messages(email, refresh_token, client_id)
            for msg in messages:
                sender = str(msg.get("from") or "")
                subject = str(msg.get("subject") or "")
                body = str(msg.get("message") or "")
                received_at = parse_dongvan_date(msg.get("date"))
                if not received_at or received_at < threshold:
                    continue
                if not is_rockstar_mail(sender, subject, body):
                    continue
                preferred = str(msg.get("code")) if msg.get("code") is not None else None
                code = extract_otp(body, preferred)
                if not code:
                    continue
                codes.append(
                    {
                        "code": code,
                        "time": relative_time(received_at),
                        "is_new": received_at >= datetime.now(timezone.utc) - timedelta(minutes=3),
                    }
                )
            return codes

    access_token = get_access_token(refresh_token, client_id)
    for msg in fetch_graph_messages(access_token):
        sender = msg.get("from", {}).get("emailAddress", {}).get("address", "")
        subject = msg.get("subject") or ""
        body = f"{msg.get('body', {}).get('content', '')} {msg.get('bodyPreview', '')}"
        received_raw = msg.get("receivedDateTime")
        received_at = (
            datetime.fromisoformat(received_raw.replace("Z", "+00:00")) if received_raw else None
        )
        if not received_at or received_at < threshold:
            continue
        if not is_rockstar_mail(sender, subject, body):
            continue
        code = extract_otp(body)
        if not code:
            continue
        codes.append(
            {
                "code": code,
                "time": relative_time(received_at),
                "is_new": received_at >= datetime.now(timezone.utc) - timedelta(minutes=3),
            }
        )
    return codes


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    refresh_token, client_id = resolve_tokens(request)
    if request.auth_mode == "oauth2":
        try:
            get_access_token(refresh_token, client_id)
        except HTTPException:
            fetch_dongvan_messages(request.email, refresh_token, client_id)
        return LoginResponse(success=True)

    get_access_token(refresh_token, client_id)
    return LoginResponse(success=True)


@app.post("/api/pull-code")
async def pull_code(request: PullCodeRequest) -> StreamingResponse:
    def stream() -> Iterator[str]:
        try:
            yield sse({"type": "status", "message": f"🔍 กำลังเข้าสู่ระบบ {request.email}..."})
            refresh_token, client_id = resolve_tokens(request)
            yield sse({"type": "status", "message": f"📬 กำลังค้นหาโค้ดของ {request.email}..."})
            codes = collect_codes(
                email=request.email,
                auth_mode=request.auth_mode,
                refresh_token=refresh_token,
                client_id=client_id,
            )
            if not codes:
                yield sse({"type": "status", "message": "ยังไม่พบโค้ดใน 30 นาทีล่าสุด"})
                yield sse({"type": "complete"})
                return
            yield sse({"type": "all_codes", "codes": codes})
        except HTTPException as exc:
            yield sse({"type": "error", "message": str(exc.detail)})
        except Exception:
            yield sse({"type": "error", "message": "ไม่สามารถดึงโค้ดได้ กรุณาลองใหม่"})

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
