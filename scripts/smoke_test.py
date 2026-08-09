from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE_URL = os.getenv("EDUCODE_BASE_URL", "http://localhost:8000").rstrip("/")
EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "admin@educode.com")
PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD", "")


def request_json(
    path: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    token: str = "",
) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} retornou HTTP {exc.code}: {payload[:500]}") from exc


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    live = request_json("/api/v1/health/live")
    checks.append(("liveness", live.get("status") == "alive", str(live)))
    ready = request_json("/api/v1/health/ready")
    checks.append(("readiness", ready.get("status") == "ready", str(ready)))

    if not PASSWORD:
        print("Health checks concluídos. Defina INITIAL_ADMIN_PASSWORD para validar autenticação.")
    else:
        tokens = request_json(
            "/api/v1/auth/login",
            method="POST",
            body={"email": EMAIL, "password": PASSWORD},
        )
        access_token = str(tokens.get("access_token", ""))
        checks.append(
            ("login", bool(access_token), "token recebido" if access_token else "token ausente")
        )
        if access_token:
            profile = request_json("/api/v1/auth/me", token=access_token)
            checks.append(
                ("profile", profile.get("email") == EMAIL.lower(), str(profile.get("email")))
            )
            version = request_json("/api/v1/platform/version", token=access_token)
            checks.append(
                (
                    "platform_version",
                    version.get("migration_revision") == "0060_enrollment_documents",
                    str(version),
                )
            )
            observability = request_json("/api/v1/observability/overview", token=access_token)
            checks.append(
                (
                    "observability",
                    bool(observability.get("generated_at")),
                    str(observability.get("platform_status")),
                )
            )

    failed = [item for item in checks if not item[1]]
    for name, ok, detail in checks:
        print(f"[{'OK' if ok else 'FALHA'}] {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
