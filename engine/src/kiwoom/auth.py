"""키움 REST API OAuth 2.0 토큰 발급/캐시 모듈.

키움 OpenAPI는 client_credentials 방식으로 access token을 발급한다.
본 모듈은 토큰을 발급받아 인메모리 + 파일(`data/.token_cache.json`)에
캐싱하고, 만료 5분 전부터 자동 갱신한다.

사용 예::

    from src.kiwoom.auth import KiwoomAuth

    auth = KiwoomAuth()
    token = await auth.get_access_token()
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final

import httpx
from loguru import logger
from pydantic import BaseModel, Field

from src.kiwoom.config import KiwoomConfig, config as default_config

_TOKEN_PATH: Final[str] = "/oauth2/token"
_CACHE_FILE: Final[Path] = Path("data/.token_cache.json")
_REFRESH_MARGIN: Final[timedelta] = timedelta(minutes=5)
_KIWOOM_DT_FORMAT: Final[str] = "%Y%m%d%H%M%S"


class KiwoomAuthError(RuntimeError):
    """키움 OAuth 인증 실패 시 발생하는 예외."""


class TokenResponse(BaseModel):
    """키움 OAuth 토큰 발급 API 응답 스키마.

    Attributes:
        token: 발급된 access token 문자열.
        token_type: 토큰 타입 (보통 "bearer").
        expires_dt: 만료 시각, "YYYYMMDDHHMMSS" 형식 문자열.
    """

    token: str
    token_type: str = Field(default="bearer")
    expires_dt: str

    def expires_at(self) -> datetime:
        """`expires_dt` 문자열을 datetime으로 파싱하여 반환한다."""
        return datetime.strptime(self.expires_dt, _KIWOOM_DT_FORMAT)


class _CachedToken(BaseModel):
    """파일/메모리에 보관하는 토큰 캐시 엔트리."""

    token: str
    expires_at: datetime
    base_url: str

    def is_valid(self, base_url: str, now: datetime) -> bool:
        """주어진 base_url 기준으로 캐시가 아직 유효한지 검사한다.

        Args:
            base_url: 현재 요청에 사용할 base URL (실전/모의 분리).
            now: 현재 시각.

        Returns:
            base_url이 일치하고 만료 5분 전까지 여유가 있으면 True.
        """
        return self.base_url == base_url and self.expires_at - _REFRESH_MARGIN > now


def _mask(token: str) -> str:
    """토큰 로그 출력 시 사용할 마스킹 헬퍼 (앞 6자만 노출)."""
    if len(token) <= 6:
        return "***"
    return f"{token[:6]}...({len(token)}자)"


class KiwoomAuth:
    """키움 REST API OAuth 토큰 관리 클래스.

    인메모리 캐시와 파일 캐시(`data/.token_cache.json`)를 함께 사용해
    동일 토큰을 24시간 동안 재사용한다. 만료 5분 전부터는 자동으로
    새 토큰을 발급받는다.

    Attributes:
        config: 키움 설정 객체. 미지정 시 모듈 싱글톤 `config`를 사용.
        cache_file: 토큰 캐시 파일 경로. 테스트 격리를 위해 주입 가능.
    """

    def __init__(
        self,
        config: KiwoomConfig | None = None,
        cache_file: Path = _CACHE_FILE,
    ) -> None:
        self.config: KiwoomConfig = config or default_config
        self.cache_file: Path = cache_file
        self._cached: _CachedToken | None = None

    async def get_access_token(self, *, force_refresh: bool = False) -> str:
        """유효한 access token 문자열을 반환한다.

        우선순위: 인메모리 캐시 → 파일 캐시 → 신규 발급.
        `force_refresh=True`이면 캐시를 무시하고 신규 발급한다.

        Args:
            force_refresh: True면 기존 캐시를 버리고 재발급.

        Returns:
            access token 평문 문자열.

        Raises:
            KiwoomAuthError: 발급 요청이 실패하거나 응답 검증이 실패한 경우.
        """
        now = datetime.now()
        base_url = self.config.base_url

        if not force_refresh:
            cached = self._cached or self._load_cache()
            if cached and cached.is_valid(base_url, now):
                self._cached = cached
                logger.debug(
                    "토큰 캐시 사용 (만료: {expires}, token={t})",
                    expires=cached.expires_at,
                    t=_mask(cached.token),
                )
                return cached.token

        token_resp = await self._fetch_new_token()
        cached = _CachedToken(
            token=token_resp.token,
            expires_at=token_resp.expires_at(),
            base_url=base_url,
        )
        self._cached = cached
        self._save_cache(cached)
        logger.info(
            "신규 토큰 발급 완료 (만료: {expires}, token={t})",
            expires=cached.expires_at,
            t=_mask(cached.token),
        )
        return cached.token

    def invalidate(self) -> None:
        """인메모리/파일 캐시를 모두 삭제한다.

        강제 재발급이 필요하거나 테스트 격리가 필요할 때 사용한다.
        """
        self._cached = None
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.debug("토큰 캐시 파일 삭제: {p}", p=self.cache_file)

    async def _fetch_new_token(self) -> TokenResponse:
        """키움 서버에 토큰 발급 요청을 보내고 응답을 검증해 반환한다."""
        url = f"{self.config.base_url}{_TOKEN_PATH}"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.config.get_app_key(),
            "secretkey": self.config.get_secret_key(),
        }
        headers = {"Content-Type": "application/json;charset=UTF-8"}

        logger.debug("토큰 발급 요청: {url} (mode={mode})", url=url, mode=self.config.mode)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise KiwoomAuthError(f"토큰 발급 HTTP 오류: {exc}") from exc

        if response.status_code != 200:
            raise KiwoomAuthError(
                f"토큰 발급 실패 status={response.status_code} body={response.text[:300]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise KiwoomAuthError(f"토큰 응답이 JSON이 아님: {response.text[:300]}") from exc

        # 키움은 HTTP 200 본문에 return_code/return_msg 형식으로 오류를 반환한다.
        return_code = data.get("return_code")
        if return_code not in (None, 0):
            raise KiwoomAuthError(
                f"키움 인증 거부 return_code={return_code} return_msg={data.get('return_msg')}"
            )

        try:
            return TokenResponse.model_validate(data)
        except Exception as exc:
            raise KiwoomAuthError(f"토큰 응답 스키마 검증 실패: {data}") from exc

    def _load_cache(self) -> _CachedToken | None:
        """파일 캐시를 읽어 `_CachedToken`을 반환한다. 손상/부재 시 None."""
        if not self.cache_file.exists():
            return None
        try:
            raw = json.loads(self.cache_file.read_text(encoding="utf-8"))
            return _CachedToken.model_validate(raw)
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            logger.warning("토큰 캐시 파일 손상, 무시: {err}", err=exc)
            return None

    def _save_cache(self, cached: _CachedToken) -> None:
        """`_CachedToken`을 파일에 JSON으로 저장한다."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(
            cached.model_dump_json(),
            encoding="utf-8",
        )
        try:
            self.cache_file.chmod(0o600)
        except OSError:
            pass


auth = KiwoomAuth()
