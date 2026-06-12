"""키움 REST API 환경설정 모듈.

.env 파일에서 환경변수를 읽어 KiwoomConfig 싱글톤 인스턴스를 제공한다.
실전/모의 모드 전환과 API 키 보호(SecretStr)를 담당한다.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class KiwoomConfig(BaseSettings):
    """키움 REST API 클라이언트 환경설정 클래스.

    .env 파일 또는 OS 환경변수에서 설정값을 자동으로 로드한다.
    pydantic-settings v2의 BaseSettings를 상속하며, case_sensitive=False
    옵션으로 대소문자 구분 없이 환경변수를 매핑한다.

    Attributes:
        app_key: 키움 OpenAPI App Key (KIWOOM_APP_KEY).
        secret_key: 키움 OpenAPI Secret Key (KIWOOM_SECRET_KEY, SecretStr로 보호).
        mode: API 호출 모드, "real"(실전) 또는 "mock"(모의), 기본값 "real".
        log_level: loguru 로그 레벨 (LOG_LEVEL), 기본값 "INFO".
        report_output_dir: 분석 리포트 출력 디렉터리 경로, 기본값 "./reports".
    """

    app_key: str = Field(validation_alias="KIWOOM_APP_KEY")
    secret_key: SecretStr = Field(validation_alias="KIWOOM_SECRET_KEY")
    mode: Literal["real", "mock"] = Field(default="real", validation_alias="KIWOOM_MODE")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    report_output_dir: Path = Field(default=Path("./reports"), validation_alias="REPORT_OUTPUT_DIR")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="",
        extra="ignore",
    )

    @property
    def base_url(self) -> str:
        """현재 mode에 해당하는 키움 REST API 베이스 URL을 반환한다.

        Returns:
            mode가 "real"이면 실전 서버 URL, "mock"이면 모의투자 서버 URL.
        """
        if self.mode == "real":
            return "https://api.kiwoom.com"
        return "https://mockapi.kiwoom.com"

    def get_app_key(self) -> str:
        """App Key 원문을 반환한다 (마스킹 없음).

        Returns:
            평문 App Key 문자열. 로그 출력 시 노출에 주의해야 한다.
        """
        return self.app_key

    def get_secret_key(self) -> str:
        """SecretStr로 감싸진 Secret Key의 원문 값을 반환한다.

        Returns:
            평문 Secret Key 문자열. API 인증 호출 시에만 사용하고,
            로그·리포트 등 외부 출력에는 절대 포함하지 않아야 한다.
        """
        return self.secret_key.get_secret_value()


config = KiwoomConfig()
