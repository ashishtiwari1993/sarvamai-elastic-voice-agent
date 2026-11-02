"""
Optional Google Sign-In gate (OIDC), restricted to one email domain.

Enabled only when GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET + SESSION_SECRET are set,
so local development without those variables stays open (no login).

Flow: /login (page) -> /auth/login -> Google -> /auth/callback -> signed session cookie.
Every route except /login, /auth/*, /api/health requires a session.
"""
import os
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
SESSION_SECRET = os.getenv("SESSION_SECRET", "").strip()
ALLOWED_DOMAIN = os.getenv("ALLOWED_EMAIL_DOMAIN", "elastic.co").strip().lower().lstrip("@")
PUBLIC_URL = os.getenv("PUBLIC_URL", "").strip().rstrip("/")  # e.g. https://xyz.run.app

ENABLED = bool(CLIENT_ID and CLIENT_SECRET and SESSION_SECRET)
OPEN_PATHS = ("/login", "/auth/", "/api/health")

LOGIN_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pratham Bank · Mitr — Sign in</title>
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-50 min-h-screen flex items-center justify-center p-4">
<div class="bg-white rounded-2xl shadow p-8 max-w-sm w-full text-center">
  <div class="text-4xl mb-2">🛡️</div>
  <h1 class="text-xl font-bold">Pratham Bank · <span class="text-orange-600">Mitr</span></h1>
  <p class="text-sm text-slate-500 mt-1 mb-6">Multilingual voice banking demo</p>
  __ERROR__
  <a href="/auth/login" class="inline-block w-full rounded-lg border border-slate-300 py-2.5 font-medium hover:bg-slate-50">
    Sign in with Google</a>
  <p class="text-xs text-slate-400 mt-4">Restricted to @__DOMAIN__ accounts.</p>
</div></body></html>"""


def _login_page(error: str = "", status: int = 200) -> HTMLResponse:
    err = f'<p class="text-sm text-red-600 mb-4">{error}</p>' if error else ""
    return HTMLResponse(LOGIN_HTML.replace("__ERROR__", err).replace("__DOMAIN__", ALLOWED_DOMAIN), status)


def setup_auth(app: FastAPI) -> None:
    if not ENABLED:
        print("🔓 Google login disabled (GOOGLE_CLIENT_ID/SECRET/SESSION_SECRET not set)")
        return
    print(f"🔐 Google login enabled — only @{ALLOWED_DOMAIN} accounts allowed")

    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    @app.middleware("http")
    async def require_login(request: Request, call_next):
        path = request.url.path
        if path.startswith(OPEN_PATHS) or request.session.get("user"):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Not signed in"}, status_code=401)
        return RedirectResponse("/login")

    # Added AFTER the auth middleware so it runs first (outermost) and request.session works.
    app.add_middleware(
        SessionMiddleware, secret_key=SESSION_SECRET, max_age=8 * 3600,
        same_site="lax", https_only=PUBLIC_URL.startswith("https://"),
    )

    def _redirect_uri(request: Request) -> str:
        return f"{PUBLIC_URL}/auth/callback" if PUBLIC_URL else str(request.url_for("auth_callback"))

    @app.get("/login")
    def login_page(request: Request, error: str = ""):
        if request.session.get("user"):
            return RedirectResponse("/")
        return _login_page(error)

    @app.get("/auth/login")
    async def auth_login(request: Request):
        # hd is only a UX hint to Google; the real check is in the callback.
        return await oauth.google.authorize_redirect(request, _redirect_uri(request), hd=ALLOWED_DOMAIN)

    @app.get("/auth/callback", name="auth_callback")
    async def auth_callback(request: Request):
        try:
            token = await oauth.google.authorize_access_token(request)
        except Exception:
            return RedirectResponse("/login?error=Sign-in+failed.+Please+try+again.")
        info = token.get("userinfo") or {}
        email = (info.get("email") or "").lower()
        ok = (
            info.get("email_verified") is True
            and email.endswith("@" + ALLOWED_DOMAIN)
            and (info.get("hd") or "").lower() == ALLOWED_DOMAIN
        )
        if not ok:
            request.session.clear()
            return _login_page(f"Only @{ALLOWED_DOMAIN} accounts can access this demo.", 403)
        request.session["user"] = {"email": email, "name": info.get("name", email)}
        return RedirectResponse("/")

    @app.get("/auth/logout")
    def auth_logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login")

    @app.get("/api/me")
    def me(request: Request):
        return request.session.get("user") or {}
