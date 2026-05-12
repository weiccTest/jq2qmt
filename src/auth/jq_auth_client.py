"""
聚宽脚本认证客户端
用于生成加密认证令牌
"""

import time
import json
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


class JQAuthClient:
    """聚宽认证客户端"""

    def __init__(self, private_key_pem):
        """初始化认证客户端

        Args:
            private_key_pem: 私钥PEM字符串
        """
        self.private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None
        )

    def generate_auth_token(self, client_id='jq_client'):
        """生成认证令牌

        Args:
            client_id: 客户端标识

        Returns:
            str: Base64编码的认证令牌
        """
        # 构造认证数据
        auth_data = {
            'client_id': client_id,
            'timestamp': int(time.time())
        }

        # 生成签名
        message = json.dumps(auth_data, sort_keys=True)
        signature = self.private_key.sign(
            message.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        # 构造令牌
        token_data = {
            'auth_data': auth_data,
            'signature': base64.b64encode(signature).decode('utf-8')
        }

        return base64.b64encode(json.dumps(token_data).encode('utf-8')).decode('utf-8')


def create_auth_headers(private_key_pem, client_id='jq_client'):
    """创建认证请求头

    Args:
        private_key_pem: 私钥PEM字符串
        client_id: 客户端标识

    Returns:
        dict: 包含认证头的字典
    """
    client = JQAuthClient(private_key_pem)
    token = client.generate_auth_token(client_id)
    return {'X-Auth-Token': token}
