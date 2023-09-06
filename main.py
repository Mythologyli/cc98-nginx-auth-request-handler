import asyncio
import datetime
import json
from urllib.parse import urlencode

import httpx
import jwt
import uvicorn
from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse

from session import Session
from utils import load_sessions_for_file, save_sessions_to_file

app = FastAPI()
config = json.load(open("config.json", "r", encoding="utf-8"))
client_id = config["client_id"]
client_secret = config["client_secret"]
saved_sessions = load_sessions_for_file()
sessions = saved_sessions
lock = asyncio.Lock()


async def remove_if_unused(session: Session):
    await asyncio.sleep(60 * 60)
    if session.user_id == -1:
        async with lock:
            sessions.remove(session)


@app.get("/")
async def index():
    return PlainTextResponse("CC98 Nginx Auth Request Handler")


@app.get("/login")
async def login(url: str):
    session = Session(url=url)

    encoded_url = urlencode({
        "client_id": client_id,
        "response_type": "code",
        "scope": "openid profile",
        "redirect_uri": f"{session.base_url()}/oauth2/callback",
        "state": session.state,
    })

    redirect_url = "https://openid.cc98.org/connect/authorize?" + encoded_url
    webvpn_redirect_url = "http://openid-cc98-org-s.webvpn.zju.edu.cn:8001/connect/authorize?" + encoded_url

    html_content = open("redirect.html", "r", encoding="utf-8").read()
    if "{{url}}" in html_content:
        html_content = html_content.replace("{{url}}", session.url)
    if "{{redirect_url}}" in html_content:
        html_content = html_content.replace("{{redirect_url}}", redirect_url)
    if "{{webvpn_redirect_url}}" in html_content:
        html_content = html_content.replace("{{webvpn_redirect_url}}", webvpn_redirect_url)

    async with lock:
        sessions.append(session)

    asyncio.create_task(remove_if_unused(session))

    return HTMLResponse(content=html_content)


@app.get("/auth")
async def auth(request: Request):
    session_id = request.cookies.get("session_id")

    response = Response()

    if session_id is None:
        response.status_code = 401
        print("Session not found")
        return response
    else:
        matched_session = None

        async with lock:
            for session in sessions:
                if session.session_id == session_id:
                    matched_session = session
                    break

        if matched_session is not None:
            if matched_session.user_id == -1:
                response.status_code = 401
                response.delete_cookie(key="session_id")
                print(f"Session {matched_session.session_id} not logged in")
            elif matched_session.is_expired(config["expires"]):
                response.status_code = 401
                response.delete_cookie(key="session_id")
                print(f"Session {matched_session.session_id} expired")
            else:
                response.status_code = 200
                print(f"Session {matched_session.session_id} is valid, user {matched_session.user_name}")
        else:
            response.status_code = 401
            response.delete_cookie(key="session_id")
            print(f"Session {session_id} not found")

    return response


@app.get("/oauth2/callback")
async def callback(code: str, state: int):
    matched_session = None

    async with lock:
        for session in sessions:
            if session.state == state:
                matched_session = session
                break

    if matched_session is not None:
        if matched_session.state == state:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        url="https://openid.cc98.org/connect/token",
                        data={
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "code": code,
                            "grant_type": "authorization_code",
                            "redirect_uri": f"{matched_session.base_url()}/oauth2/callback"
                        },
                        timeout=10
                    )
                except httpx.HTTPError:
                    return PlainTextResponse("Error occurred when requesting token from CC98")

                if response.status_code != 200:
                    return PlainTextResponse("Cannot get token from CC98")

                response_data = response.json()
                id_token = response_data["id_token"]

                id_token_decode = jwt.decode(id_token, options={"verify_signature": False})
                matched_session.user_id = id_token_decode["sub"]
                matched_session.user_name = id_token_decode["name"]

                saved_sessions.append(matched_session)
                save_sessions_to_file(saved_sessions)

                print(
                    f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"User {matched_session.user_name} logged in {matched_session.url}"
                )

                response = RedirectResponse(matched_session.url)
                response.set_cookie(
                    key="session_id",
                    value=matched_session.session_id,
                    expires=config["expires"],
                )

                return response
    else:
        return PlainTextResponse("Cannot find session with the given state")


log_config = uvicorn.config.LOGGING_CONFIG
log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"

uvicorn.run(app, host=config["host"], port=config["port"], log_config=log_config)
