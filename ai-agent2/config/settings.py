from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM 配置
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "qwen3-max"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2000
    LLM_REQUEST_TIMEOUT: int = 60
    
    # Redis 配置
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # 服务配置
    AGENT_HOST: str = "0.0.0.0"
    AGENT_PORT: int = 8000
    SPRING_GATEWAY_URL: str = "http://localhost:9000"
    
    # Nacos 配置
    NACOS_SERVER: str = "127.0.0.1:8848"
    NACOS_NAMESPACE: str = "public"
    NACOS_GROUP: str = "com.social"
    NACOS_SERVICE_NAME: str = "ai-agent"
    NACOS_USERNAME: str = ""
    NACOS_PASSWORD: str = ""
    # 注册 IP 已改为自动检测（nacos_client.py 启动时根据 NACOS_SERVER 地址自动推断），无需手动配置
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

settings = Settings()