"""Send a test prompt to a running llama-server and log the completion."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = ROOT / "logs" / "gemma-server-reply.json"


def query_server(
    url: str,
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    log_path: Path | None = None,
) -> dict:
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers)

    start_time = time.time()
    try:
        with urllib.request.urlopen(request) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
    except urllib.error.URLError as error:
        print(f"[error] Failed to connect to server at {url}: {error}", file=sys.stderr)
        raise

    duration = time.time() - start_time
    result = json.loads(body)
    content = result["choices"][0]["message"]["content"]

    record = {
        "status_code": status_code,
        "duration_seconds": duration,
        "prompt": prompt,
        "reply": content,
        "usage": result.get("usage", {}),
        "raw_response": result,
    }

    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, ensure_ascii=False)

    return record


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query local OpenAI-compatible llama-server endpoint."
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8080/v1/chat/completions",
        help="API endpoint URL (default: %(default)s)",
    )
    parser.add_argument(
        "--prompt",
        default="Are you ready to help?",
        help="Prompt message to send (default: %(default)s)",
    )
    parser.add_argument(
        "--model",
        default="gemma-4-E4B-it-Q4_K_M",
        help="Model identifier (default: %(default)s)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature (default: %(default)s)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="Max output tokens (default: %(default)s)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help="Path to save response JSON log (default: %(default)s)",
    )

    arguments = parser.parse_args()

    print(f"Connecting to {arguments.url} with model '{arguments.model}'...")
    try:
        record = query_server(
            url=arguments.url,
            prompt=arguments.prompt,
            model=arguments.model,
            temperature=arguments.temperature,
            max_tokens=arguments.max_tokens,
            log_path=arguments.log_file,
        )
    except Exception:
        return 1

    print(f"Status Code: {record['status_code']}")
    print(f"Roundtrip Time: {record['duration_seconds']:.2f}s")
    if arguments.log_file:
        print(f"Logged reply to: {arguments.log_file}")

    print("\n=== Model Reply ===")
    # Print safe for any console encoding
    safe_reply = record["reply"].encode(
        sys.stdout.encoding or "utf-8", errors="backslashreplace"
    ).decode(sys.stdout.encoding or "utf-8")
    print(safe_reply)

    usage = record.get("usage", {})
    if usage:
        print(
            f"\n[Tokens] prompt={usage.get('prompt_tokens')}, "
            f"completion={usage.get('completion_tokens')}, "
            f"total={usage.get('total_tokens')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
