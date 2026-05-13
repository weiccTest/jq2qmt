# 聚宽研究环境脚本 - 因子数据同步到MySQL
# 功能：获取因子数据并通过API保存到远程数据库
#
# 使用说明：
# 1. 修改 SERVER_URL 为你的服务地址
# 2. 在聚宽研究环境运行此脚本

import pandas as pd
import numpy as np
import time
import requests
import json
import base64
from jqdata import *
import jqfactor

# cryptography 库用于加密认证
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


# ============== 配置参数 ==============
SERVER_URL = 'http://119.29.53.207:5366'  # 服务地址
REQUEST_TIMEOUT = 30

# 指数代码
INDEX_CODE = '000985.XSHG'  # 中证全指

# 每批获取股票数量
BATCH_SIZE = 100

# 导出日期（None表示最近一个有数据的交易日，即前一个交易日）
EXPORT_DATE = None  # 或指定日期如 '2024-04-26'

# 私钥（用于生成认证令牌）
PRIVATE_KEY_PEM = '''
-----BEGIN PRIVATE KEY-----
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
7CN6YyUX2bMgSufwtANDwZbjgnbyOQ==
-----END PRIVATE KEY-----
'''


# ==================== 认证模块 ====================
class JQAuthClient:
    """聚宽认证客户端"""

    def __init__(self, private_key_pem):
        self.private_key = serialization.load_pem_private_key(
            private_key_pem.strip().encode('utf-8'),
            password=None,
            backend=default_backend()
        )

    def generate_auth_token(self, client_id='jq_factor'):
        """生成认证令牌"""
        auth_data = {
            'client_id': client_id,
            'timestamp': int(time.time())
        }
        message = json.dumps(auth_data, sort_keys=True)
        signature = self.private_key.sign(
            message.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        token_data = {
            'auth_data': auth_data,
            'signature': base64.b64encode(signature).decode('utf-8')
        }
        return base64.b64encode(json.dumps(token_data).encode('utf-8')).decode('utf-8')

    def get_auth_headers(self, client_id='jq_factor'):
        """获取认证请求头"""
        return {'X-Auth-Token': self.generate_auth_token(client_id)}


# 全局认证客户端
_auth_client = None

def get_auth_client():
    """获取认证客户端实例"""
    global _auth_client
    if _auth_client is None:
        _auth_client = JQAuthClient(PRIVATE_KEY_PEM)
    return _auth_client


def auth_request(method, url, **kwargs):
    """带认证的请求封装"""
    client = get_auth_client()
    headers = kwargs.pop('headers', {})
    headers.update(client.get_auth_headers())
    kwargs['headers'] = headers
    kwargs['timeout'] = kwargs.get('timeout', REQUEST_TIMEOUT)
    return requests.request(method, url, **kwargs)


# ==================== 因子列表 ====================
FACTOR_LIST = [
    'cube_of_size',
    'MFI14',
    'Skewness20',
    'financial_assets',
    'bear_power',
    'PSY',
    'Kurtosis120',
    'VMACD',
    'single_day_VPT',
    'interest_free_current_liability',
    'BIAS60',
    'ATR6',
    'sales_to_price_ratio',
    'cash_flow_to_price_ratio',
    'Rank1M',
    'Kurtosis60',
    'fifty_two_week_close_rank',
    'arron_up_25',
    'Kurtosis20',
    'daily_standard_deviation',
    'Skewness60',
    'single_day_VPT_12',
    'earnings_yield',
    'leverage',
    'CR20',
    'VOSC',
    'price_no_fq',
    'Variance20',
    'WVAD',
    'ROC120',
    'money_flow_20',
    'circulating_market_cap',
    'book_to_price_ratio',
    'MAWVAD',
    'ATR14',
    'turnover_volatility',
    'momentum',
    'MASS',
    'VEMA5',
    'DAVOL5',
    'natural_log_of_market_cap',
    'arron_down_25',
    'VDIFF',
    'liquidity',
]


def export_factor_data():
    """导出因子数据并通过API保存"""

    # 1. 确定日期
    if EXPORT_DATE:
        end_date = EXPORT_DATE
    else:
        end_date = pd.Timestamp.today().strftime('%Y-%m-%d')

    print("导出日期: %s" % end_date)
    print("因子数量: %d" % len(FACTOR_LIST))

    # 2. 获取股票池
    print("\n[1/4] 获取股票池...")
    if EXPORT_DATE:
        trade_date = get_trade_days(end_date=EXPORT_DATE, count=1)[0]
    else:
        trade_dates = get_trade_days(end_date=pd.Timestamp.today().strftime('%Y-%m-%d'), count=2)
        trade_date = trade_dates[0]
    print("   trade_date=%s" % trade_date)
    stock_list = get_index_stocks(INDEX_CODE, date=trade_date)
    print("   股票数量: %d" % len(stock_list))

    # 3. 过滤股票
    print("\n[2/4] 过滤股票...")
    stock_list = filter_stocks(stock_list, trade_date)
    print("   过滤后数量: %d" % len(stock_list))

    # 获取股票名称映射
    all_securities = get_all_securities(date=trade_date)
    stock_name_map = {code: all_securities.loc[code, 'display_name']
                      for code in stock_list if code in all_securities.index}

    # 4. 分批获取因子数据并发送
    print("\n[3/4] 获取因子数据并同步到数据库...")
    total_count = 0
    total_batches = (len(stock_list) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(stock_list), BATCH_SIZE):
        batch_stocks = stock_list[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        print("   批次 %d/%d: 处理 %d 只股票..." % (batch_num, total_batches, len(batch_stocks)))

        try:
            batch_data = jqfactor.get_factor_values(
                securities=batch_stocks,
                factors=FACTOR_LIST,
                end_date=trade_date,
                count=1
            )

            if batch_data is not None and len(batch_data) > 0:
                records = process_factor_data(batch_data, batch_stocks, FACTOR_LIST, trade_date, stock_name_map)

                if records:
                    if batch_num == 1:
                        print("      前5条数据预览:")
                        for idx, r in enumerate(records[:5]):
                            print("         [%d] %s %s: %d 个因子" % (idx+1, r['stock_code'], r['stock_name'], len(r['factors'])))
                    count = send_to_server(records)
                    total_count += count
                    print("      批次 %d 同步成功: %d 条" % (batch_num, count))
            else:
                print("      批次 %d 返回空数据" % batch_num)

        except Exception as e:
            print("      批次 %d 失败: %s" % (batch_num, str(e)))
            import traceback
            traceback.print_exc()

        time.sleep(0.5)

    print("\n" + "="*50)
    print("同步完成!")
    print("="*50)
    print("交易日期: %s" % trade_date)
    print("同步记录数: %d" % total_count)

    return total_count


def process_factor_data(factor_result, stock_list, factor_list, trade_date, stock_name_map):
    """处理 jqfactor 返回的因子数据，转换为API所需格式"""
    records = []

    if isinstance(factor_result, dict):
        for stock in stock_list:
            factors = {}
            for factor_name, factor_df in factor_result.items():
                if factor_df is not None and len(factor_df) > 0:
                    values = factor_df.iloc[-1] if len(factor_df) > 1 else factor_df.iloc[0]
                    if stock in values.index:
                        val = values[stock]
                        factors[factor_name] = None if pd.isna(val) else float(val)

            if factors:
                records.append({
                    'trade_date': str(trade_date),
                    'stock_code': stock,
                    'stock_name': stock_name_map.get(stock, ''),
                    'factors': factors
                })

    return records


def send_to_server(records):
    """发送数据到服务器"""
    try:
        resp = auth_request('POST', SERVER_URL + '/api/v1/jq/save_factors_batch', json={'records': records})
        result = resp.json()
        if result.get('code') == 0:
            return result.get('count', 0)
        else:
            print("      服务器错误: %s" % result.get('msg', ''))
            return 0
    except Exception as e:
        print("      发送失败: %s" % str(e))
        return 0


def filter_stocks(stock_list, date):
    """过滤股票"""
    all_securities = get_all_securities(date=date)

    try:
        price_df = get_price(stock_list, end_date=date, frequency='daily',
                            fields=['close', 'high_limit', 'low_limit'],
                            count=1, panel=False)
        limit_dict = {}
        for _, row in price_df.iterrows():
            limit_dict[row['code']] = {
                'close': row['close'],
                'high_limit': row['high_limit'],
                'low_limit': row['low_limit']
            }
    except:
        limit_dict = {}

    filtered = []
    for stock in stock_list:
        code = stock.split('.')[0]

        if code.startswith(('68', '4', '8')):
            continue

        if stock not in all_securities.index:
            continue

        stock_info = all_securities.loc[stock]

        if 'ST' in stock_info.display_name or '*' in stock_info.display_name:
            continue

        if '退' in stock_info.display_name:
            continue

        if stock in limit_dict:
            info = limit_dict[stock]
            if info['close'] >= info['high_limit'] or info['close'] <= info['low_limit']:
                continue

        filtered.append(stock)

    return filtered


# 运行
df = export_factor_data()
