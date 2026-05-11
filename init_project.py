#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JQ-QMT 项目初始化脚本

此脚本将引导您完成项目的初始化配置，包括：
1. 生成 config.py 配置文件
2. 生成 RSA 密钥对
3. 生成 jq_config.py 配置文件
4. 配置 API_URL
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
# from urllib.parse import URL


class ProjectInitializer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.src_dir = self.project_root / 'src'
        self.api_dir = self.src_dir / 'api'
        
    def print_banner(self):
        """打印欢迎横幅"""
        print("="*60)
        print("    JQ-QMT 项目初始化向导")
        print("="*60)
        print("此向导将帮助您完成项目的初始化配置")
        print("请按照提示逐步完成配置...")
        print()
        
    def check_prerequisites(self):
        """检查前置条件"""
        print("[1/5] 检查前置条件...")
            
        # 检查 Python 版本
        if sys.version_info < (3, 6):
            print("✗ 错误: 需要 Python 3.6 或更高版本")
            return False
        print(f"✓ Python {sys.version.split()[0]} 版本符合要求")
        
        print()
        return True
        
    def generate_keys(self):
        """生成 RSA 密钥对"""
        print("[2/5] 生成 RSA 密钥对...")
        
        private_key_file = self.project_root / "quant_id_rsa_pkcs8.pem"
        public_key_file = self.project_root / "quant_id_rsa_public.pem"
        temp_key_file = self.project_root / "quant_id_rsa_new.pem"
        
        # 检查是否已存在密钥文件
        existing_files = []
        for key_file in [private_key_file, public_key_file, temp_key_file]:
            if key_file.exists():
                existing_files.append(key_file.name)
                
        if existing_files:
            print(f"发现已存在的密钥文件: {', '.join(existing_files)}")
            overwrite = input("是否覆盖现有文件? (y/N): ").strip().lower()
            if overwrite != 'y':
                print("跳过密钥生成")
                print()
                return True
                
        try:
            # 生成原始私钥
            print("正在生成 4096 位 RSA 私钥...")
            subprocess.run([
                'openssl', 'genrsa', '-out', str(temp_key_file), '4096'
            ], check=True, capture_output=True)
            
            # 转换为 PKCS#8 格式
            print("转换为 PKCS#8 格式...")
            subprocess.run([
                'openssl', 'pkcs8', '-topk8', '-inform', 'PEM', '-outform', 'PEM',
                '-nocrypt', '-in', str(temp_key_file), '-out', str(private_key_file)
            ], check=True, capture_output=True)
            
            # 生成公钥
            print("生成对应的公钥...")
            subprocess.run([
                'openssl', 'rsa', '-in', str(temp_key_file), '-pubout',
                '-out', str(public_key_file)
            ], check=True, capture_output=True)
            
            # 删除临时文件
            temp_key_file.unlink()
            
            print("✓ RSA 密钥对生成成功")
            print(f"  - 私钥文件: {private_key_file.name}")
            print(f"  - 公钥文件: {public_key_file.name}")
            
        except subprocess.CalledProcessError as e:
            print(f"✗ 密钥生成失败: {e}")
            return False
            
        print()
        return True
        
    def configure_database(self):
        """配置数据库信息"""
        print("[3/5] 配置数据库连接...")
        
        print("请输入数据库连接信息:")
        db_host = "119.29.53.207"
        db_port = "3306"
        db_username = "root"
        db_password = "!Q@W123456"
        db_name = "quant"
        
        try:
            db_port = int(db_port)
        except ValueError:
            print("✗ 端口号必须是数字")
            return False
            
        if not db_username:
            print("✗ 数据库用户名不能为空")
            return False
            
        self.db_config = {
            'host': db_host,
            'port': db_port,
            'username': db_username,
            'password': db_password,
            'database': db_name
        }
        
        print("✓ 数据库配置完成")
        print()
        return True
        
    def configure_api(self):
        """配置 API 信息"""
        print("[4/5] 配置 API 服务...")
        
        print("API 服务配置将使用默认值:")
        api_host = "0.0.0.0"
        api_port = "5366"
        print(f"  - 服务主机地址: {api_host}")
        print(f"  - 服务端口: {api_port}")
        
        # 配置外部访问地址
        print("\n请输入外部访问地址（用于聚宽端和QMT端连接）:")
        external_host = input("服务器IP地址: ").strip()
        if not external_host:
            print("✗ 服务器IP地址不能为空")
            return False
        external_port = input(f"外部访问端口 [{80}]: ").strip() or 80
        
        try:
            api_port = int(api_port)
            external_port = int(external_port)
        except ValueError:
            print("✗ 端口号必须是数字")
            return False
            
        # 配置加密认证
        print("\n加密认证配置:")
        print("默认启用RSA加密认证（推荐）")
        use_crypto = True
        simple_api_key = "your-simple-api-key-here"
                
        self.api_config = {
            'host': api_host,
            'port': api_port,
            'external_host': external_host,
            'external_port': external_port,
            'use_crypto': use_crypto,
            'simple_api_key': simple_api_key
        }
        
        print("✓ API 配置完成")
        print()
        return True
        
    def generate_config_files(self):
        """生成配置文件"""
        print("[5/5] 生成配置文件...")
        
        # 生成 config.py
        config_content = f'''# -*- coding: utf-8 -*-
"""
JQ-QMT 项目配置文件
自动生成于项目初始化
"""

from sqlalchemy.engine import URL

# 数据库配置
DB_CONFIG = {{
    'drivername': 'mysql+pymysql',
    'host': '{self.db_config["host"]}',
    'username': '{self.db_config["username"]}',
    'password': '{self.db_config["password"]}',
    'database': '{self.db_config["database"]}',
    'port': {self.db_config["port"]}
}}

# SQLAlchemy配置
SQLALCHEMY_DATABASE_URI = URL.create(**DB_CONFIG)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# API配置
API_HOST = '{self.api_config["host"]}'
API_PORT = {self.api_config["port"]}
API_PREFIX = '/api/v1'

# 加密认证配置
CRYPTO_AUTH_CONFIG = {{
    # 是否启用加密认证（True: 启用, False: 禁用）
    'ENABLED': {self.api_config["use_crypto"]},
    
    # 密钥文件路径（相对于项目根目录）
    'PRIVATE_KEY_FILE': 'quant_id_rsa_pkcs8.pem',  # PKCS#8格式私钥文件
    'PUBLIC_KEY_FILE': 'quant_id_rsa_public.pem',   # X.509格式公钥文件
    
    'TOKEN_MAX_AGE': 300,  # 令牌有效期（秒）
    
    # 当加密禁用时的简单API密钥（可选）
    'SIMPLE_API_KEY': '{self.api_config["simple_api_key"]}'
}}
'''
        
        config_file = self.src_dir / 'config.py'
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print(f"✓ 生成 {config_file.relative_to(self.project_root)}")
        
        # 生成 jq_config.py
        # 构建API URL，如果是80端口则不拼接端口
        if self.api_config['external_port'] == 80:
            api_url = f"http://{self.api_config['external_host']}"
        else:
            api_url = f"http://{self.api_config['external_host']}:{self.api_config['external_port']}"
        jq_config_content = f'''# -*- coding: utf-8 -*-
"""
聚宽端配置文件
请将此文件复制到聚宽研究环境的根目录
"""

API_URL = "{api_url}"  # 服务器API地址
USE_CRYPTO_AUTH = {self.api_config["use_crypto"]}
PRIVATE_KEY_FILE = "quant_id_rsa_pkcs8.pem"
'''
        
        jq_config_file = self.api_dir / 'jq_config.py'
        with open(jq_config_file, 'w', encoding='utf-8') as f:
            f.write(jq_config_content)
        print(f"✓ 生成 {jq_config_file.relative_to(self.project_root)}")
        
        # 更新 qmt_jq_trade.py 中的 API_URL
        qmt_trade_file = self.api_dir / 'qmt_jq_trade'
        new_qmt_trade_file = self.api_dir / 'qmt_jq_trade.py'
        if qmt_trade_file.exists():
            with open(qmt_trade_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换 API_URL
            old_line = 'API_URL = "http://your_server_url:port"  # 服务器API地址（自动配置）'
            new_line = f'API_URL = "{api_url}"  # 服务器API地址（自动配置）'
            content = content.replace(old_line, new_line)
            
            with open(new_qmt_trade_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 更新 {qmt_trade_file.relative_to(self.project_root)} 中的 API_URL")
        
        print()
        return True
        
    def print_summary(self):
        """打印配置总结"""
        print("="*60)
        print("    配置完成！")
        print("="*60)
        print("\n生成和更新的文件:")
        print(f"  ✓ src/config.py - 主配置文件")
        print(f"  ✓ src/api/jq_config.py - 聚宽端配置文件")
        print(f"  ✓ src/api/qmt_jq_trade.py - QMT端配置文件（已更新API_URL）")
        print(f"  ✓ quant_id_rsa_pkcs8.pem - RSA私钥文件")
        print(f"  ✓ quant_id_rsa_public.pem - RSA公钥文件")
        
        print("\n下一步操作:")
        print("  1. 安装依赖: pip install -r requirements.txt")
        print("  2. 创建数据库和表结构")
        print("  3. 将 src/api/jq_config.py 和私钥文件复制到聚宽研究环境")
        print("  4. 将 src/api/qmt_jq_trade.py 复制到QMT策略中使用")
        print("  5. 启动服务: python src/app.py")
        
        api_url = f"http://{self.api_config['external_host']}:{self.api_config['external_port']}"
        print(f"\n服务访问地址: {api_url}")
        print(f"持仓查看页面: {api_url}/")
        print(f"持仓调整页面: {api_url}/adjustment")
        print(f"密码管理页面: {api_url}/password")
        
    def run(self):
        """运行初始化流程"""
        self.print_banner()
        
        if not self.check_prerequisites():
            return False
            
        if not self.generate_keys():
            return False
            
        if not self.configure_database():
            return False
            
        if not self.configure_api():
            return False
            
        if not self.generate_config_files():
            return False
            
        self.print_summary()
        return True


def main():
    """主函数"""
    try:
        initializer = ProjectInitializer()
        success = initializer.run()
        
        if success:
            print("\n🎉 项目初始化成功完成！")
            return 0
        else:
            print("\n❌ 项目初始化失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        return 1
    except Exception as e:
        print(f"\n❌ 初始化过程中发生错误: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())