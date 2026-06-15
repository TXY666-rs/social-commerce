from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # LLM 配置
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL_1: str = "qwen3-max"            # 主力模型（优先级最高）
    LLM_MODEL_2: str = "qwen-plus"             # 二级降级模型
    LLM_MODEL_3: str = "qwen-turbo"            # 三级降级模型
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2000
    LLM_REQUEST_TIMEOUT: int = 60

    @field_validator("LLM_MODEL_1", "LLM_MODEL_2", "LLM_MODEL_3", mode="before")
    @classmethod
    def empty_to_none(cls, v, info):
        """空字符串视为未配置，回退到字段默认值"""
        if v == "":
            return cls.model_fields[info.field_name].default
        return v
    
    # Redis 配置
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # 服务配置
    AGENT_HOST: str = "0.0.0.0"
    AGENT_PORT: int = 8000
    # [废弃] Spring Gateway URL —— 重构后不再调用 Java 后端，保留字段仅为向后兼容
    SPRING_GATEWAY_URL: str = ""

    # Nacos 配置（可选 —— 重构后不连 Nacos 也能正常启动）
    NACOS_SERVER: str = ""           # 留空表示不启用 Nacos 注册
    NACOS_NAMESPACE: str = "public"
    NACOS_GROUP: str = "com.social"
    NACOS_SERVICE_NAME: str = "ai-agent"
    NACOS_USERNAME: str = ""
    NACOS_PASSWORD: str = ""
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

settings = Settings()