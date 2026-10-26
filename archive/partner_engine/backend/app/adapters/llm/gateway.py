"""R30-C DeepSeek compatible tool calling transport (server-side only).

Only the public Chat Completions endpoint is called. Secrets are never put in
HTTP responses, frontend bundles, plan artifacts, or prompts. No database access.
"""
from __future__ import annotations
import os
from typing import Any
import httpx


class ModelUnavailable(RuntimeError):
    """Safe public message; never includes the provider's raw response body."""


def model_status() -> dict[str, Any]:
    return {
        'configured': bool(os.getenv('DEEPSEEK_API_KEY', '').strip()),
        'provider': 'DeepSeek',
        'model': os.getenv('DEEPSEEK_MODEL', 'deepseek-flash').strip() or 'deepseek-flash',
        'api_endpoint': 'server_side_only',
    }


class DeepSeekGateway:
    def __init__(self, *, api_key: str | None = None, client: Any = None):
        self.api_key = api_key if api_key is not None else os.getenv('DEEPSEEK_API_KEY', '').strip()
        self.model = os.getenv('DEEPSEEK_MODEL', 'deepseek-flash').strip() or 'deepseek-flash'
        self.base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').strip().rstrip('/')
        # Disallow arbitrary base URLs / URLs from an attacker-controlled env or payload.
        if self.base_url not in ('https://api.deepseek.com', 'https://api.deepseek.com/v1'):
            raise ModelUnavailable('模型服务地址必须是官方 DeepSeek HTTPS API 地址')
        self.client = client

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        if not self.api_key:
            raise ModelUnavailable('请先在后端设置 DEEPSEEK_API_KEY；未配置时可使用页面的“直接运行算法”按钮')
        payload = {
            'model': self.model, 'messages': messages, 'tools': tools,
            'tool_choice': 'auto', 'stream': False,
            'max_tokens': 1100,
            'extra_body': None,
            'thinking': {'type': 'disabled'},
        }
        payload.pop('extra_body')
        url = f'{self.base_url}/chat/completions'
        try:
            if self.client is not None:
                response = self.client.post(url, json=payload, headers={'Authorization': f'Bearer {self.api_key}'})
            else:
                with httpx.Client(timeout=httpx.Timeout(65, connect=8), follow_redirects=False, trust_env=True) as http:
                    response = http.post(url, json=payload, headers={
                        'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json',
                    })
            response.raise_for_status()
            value = response.json()
            result = value['choices'][0]['message']
            if not isinstance(result, dict):
                raise ValueError('missing model message')
            return result
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code in (401, 403):
                raise ModelUnavailable('DeepSeek API Key 无效或接口无权限，请检查后端密钥') from None
            if code == 429:
                raise ModelUnavailable('DeepSeek 请求限流或余额不足，请稍后重试') from None
            raise ModelUnavailable(f'DeepSeek 服务暂时不可用（HTTP {code}）') from None
        except (httpx.RequestError, ValueError, KeyError, IndexError, TypeError):
            raise ModelUnavailable('DeepSeek 网络连接或返回格式异常，请检查网络和模型配置') from None


def build_gateway() -> DeepSeekGateway:
    return DeepSeekGateway()
