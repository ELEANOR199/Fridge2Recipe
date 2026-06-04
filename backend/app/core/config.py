from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Fridge2Recipe Search API"
    database_url: str = "postgresql+psycopg://fridge:fridge_dev_password@localhost:5432/fridge2recipe"
    opensearch_url: str = "http://localhost:9200"
    admin_token: str = "dev-token"
    cors_allowed_origins: str = ""
    sample_data_path: str = "data/xiachufang/recipes_subset.jsonl"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        """返回允许浏览器访问 API 的前端来源列表。

        配置来自 CORS_ALLOWED_ORIGINS，格式保持为 .env 中易编辑的
        英文逗号分隔字符串，方便远程服务器部署时直接修改。
        """
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
