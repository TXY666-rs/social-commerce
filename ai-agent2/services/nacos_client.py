import socket
import logging
from v2.nacos import (
    NacosNamingService, ClientConfigBuilder, GRPCConfig,
    RegisterInstanceParam, DeregisterInstanceParam, ListInstanceParam,
)
from config.settings import settings
logger = logging.getLogger(__name__)


def _detect_local_ip(nacos_server: str) -> str:
    """自动检测本机 IP（用于 Nacos 注册）。空地址时返回 127.0.0.1"""
    if not nacos_server:
        return "127.0.0.1"
    try:
        host, port = nacos_server.rsplit(":", 1)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((host, int(port)))
            return s.getsockname()[0]
    except Exception:
        logger.warning("⚠️ 自动检测本机 IP 失败，回退到 127.0.0.1")
        return "127.0.0.1"


class NacosClient:
    """Nacos 客户端（基于 nacos-sdk-python 3.x，原生 async + gRPC 长连接）

    核心变化（对比老版 nacos-sdk-python 0.1.x）：
    - 通信协议：HTTP 短轮询 → gRPC 长连接
    - 心跳机制：手动定时心跳 → gRPC 自动保活，无需手动调用
    - API 风格：同步 + asyncio.to_thread 包装 → 原生 async/await
    - 注册 IP：自动检测，与 Spring 服务行为一致
    """

    def __init__(self):
        self.naming_client = None
        self.service_name = settings.NACOS_SERVICE_NAME
        self.register_ip = _detect_local_ip(settings.NACOS_SERVER)
        self.port = settings.AGENT_PORT
        self._started = False

    async def start(self):
        """注册服务到 Nacos（gRPC 长连接，自动心跳）"""
        try:
            client_config = (ClientConfigBuilder()
                             .server_address(settings.NACOS_SERVER)
                             .namespace_id(settings.NACOS_NAMESPACE)
                             .username(settings.NACOS_USERNAME)
                             .password(settings.NACOS_PASSWORD)
                             .log_level('INFO')
                             .grpc_config(GRPCConfig(grpc_timeout=3000))
                             .build())

            self.naming_client = await NacosNamingService.create_naming_service(client_config)

            await self.naming_client.register_instance(
                request=RegisterInstanceParam(
                    service_name=self.service_name,
                    group_name=settings.NACOS_GROUP,
                    ip=self.register_ip,
                    port=self.port,
                    weight=1.0,
                    enabled=True,
                    healthy=True,
                    ephemeral=True,
                    metadata={
                        "version": "1.0.0",
                        "preserved.register.source": "PYTHON_AI_AGENT"
                    }
                )
            )

            self._started = True
            logger.info(f"✅ 成功注册到 Nacos: {self.service_name}@{self.register_ip}:{self.port}")

        except Exception as e:
            logger.error(f"❌ 注册到 Nacos 失败: {e}")
            raise

    async def stop(self):
        """注销服务并关闭客户端"""
        self._started = False
        if self.naming_client:
            try:
                await self.naming_client.deregister_instance(
                    request=DeregisterInstanceParam(
                        service_name=self.service_name,
                        group_name=settings.NACOS_GROUP,
                        ip=self.register_ip,
                        port=self.port,
                        ephemeral=True
                    )
                )
                await self.naming_client.shutdown()
                logger.info(f"✅ 成功从 Nacos 注销: {self.service_name}")
            except Exception as e:
                logger.warning(f"⚠️ 从 Nacos 注销失败: {e}")

    async def get_service_instances(self, service_name: str, group: str = None) -> list:
        """获取服务实例列表（服务发现）"""
        if not self.naming_client:
            raise RuntimeError("Nacos 客户端未初始化")

        try:
            result = await self.naming_client.list_instances(
                ListInstanceParam(
                    service_name=service_name,
                    group_name=group or settings.NACOS_GROUP,
                    healthy_only=True
                )
            )
            return result
        except Exception as e:
            logger.error(f"获取服务实例失败: {e}")
            return []


# 全局 Nacos 客户端实例
nacos_client = NacosClient()
