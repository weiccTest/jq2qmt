/Users/weicc/code/jx_code/jq2qmt/.venv/bin/python /Users/weicc/code/jx_code/jq2qmt/init_project.py 
============================================================
    JQ-QMT 项目初始化向导
============================================================
此向导将帮助您完成项目的初始化配置
请按照提示逐步完成配置...

[1/5] 检查前置条件...
✓ Python 3.14.4 版本符合要求

[2/5] 生成 RSA 密钥对...
发现已存在的密钥文件: quant_id_rsa_pkcs8.pem, quant_id_rsa_public.pem
是否覆盖现有文件? (y/N): y
正在生成 4096 位 RSA 私钥...
转换为 PKCS#8 格式...
生成对应的公钥...
✓ RSA 密钥对生成成功
  - 私钥文件: quant_id_rsa_pkcs8.pem
  - 公钥文件: quant_id_rsa_public.pem

[3/5] 配置数据库连接...
请输入数据库连接信息:
✓ 数据库配置完成

[4/5] 配置 API 服务...
API 服务配置将使用默认值:
  - 服务主机地址: 0.0.0.0
  - 服务端口: 5366

请输入外部访问地址（用于聚宽端和QMT端连接）:
服务器IP地址: 119.29.53.207
外部访问端口 [80]: 8899

加密认证配置:
默认启用RSA加密认证（推荐）
✓ API 配置完成

[5/5] 生成配置文件...
✓ 生成 src/config.py
✓ 生成 src/api/jq_config.py
✓ 更新 src/api/qmt_jq_trade 中的 API_URL

============================================================
    配置完成！
============================================================

生成和更新的文件:
  ✓ src/config.py - 主配置文件
  ✓ src/api/jq_config.py - 聚宽端配置文件
  ✓ src/api/qmt_jq_trade.py - QMT端配置文件（已更新API_URL）
  ✓ quant_id_rsa_pkcs8.pem - RSA私钥文件
  ✓ quant_id_rsa_public.pem - RSA公钥文件

下一步操作:
  1. 安装依赖: pip install -r requirements.txt
  2. 创建数据库和表结构
  3. 将 src/api/jq_config.py 和私钥文件复制到聚宽研究环境
  4. 将 src/api/qmt_jq_trade.py 复制到QMT策略中使用
  5. 启动服务: python src/app.py

服务访问地址: http://119.29.53.207:8899
持仓查看页面: http://119.29.53.207:8899/
持仓调整页面: http://119.29.53.207:8899/adjustment
密码管理页面: http://119.29.53.207:8899/password

🎉 项目初始化成功完成！

进程已结束，退出代码为 0