# 聚宽模拟盘脚本 - 分钟数据收集
# 功能：每分钟扫描请求表，收集指定股票的分钟K线数据并发送到本地服务器
#
# 使用说明：
# 1. 修改 SERVER_URL 为你的本地服务地址
# 2. 确保聚宽已开通外网访问权限
# 3. 将此脚本复制到聚宽模拟盘运行

from jqdata import *
import requests
from datetime import datetime
import pandas as pd
import numpy as np
import time
import requests
from jqdata import *
import jqfactor


# 你的本地服务地址（需要公网IP或内网穿透）
SERVER_URL = 'http://119.29.53.207:5000'
REQUEST_TIMEOUT = 20
# 指数代码
INDEX_CODE = '000985.XSHG'  # 中证全指

# 每批获取股票数量
BATCH_SIZE = 100

# 导出日期（None表示最近一个有数据的交易日，即前一个交易日）
EXPORT_DATE = None  # 或指定日期如 '2024-04-26'


def initialize(context):
    """初始化函数"""
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    log.info('分钟数据收集服务启动')

    run_daily(export_factor_data, time='08:00', reference_security='000300.XSHG')
    # 每分钟执行 export_factor_data()
    run_daily(collect_minute_data, time='every_bar', reference_security='000300.XSHG')


def is_trading_time(current_dt):
    """判断是否在交易时间"""
    current_time = current_dt.time()
    t = lambda s: datetime.strptime(s, '%H:%M').time()
    return (t('09:30') <= current_time <= t('11:31')) or \
           (t('13:00') <= current_time <= t('15:01'))


def collect_minute_data(context):
    """每分钟扫描请求表并收集数据"""
    if not is_trading_time(context.current_dt):
        return

    try:
        # 1. 从本地服务获取股票列表
        resp = requests.get(SERVER_URL + '/get_symbols', timeout=REQUEST_TIMEOUT)
        result = resp.json()
        if result['code'] != 0:
            log.error('获取股票列表失败: ' + result.get('msg', ''))
            return

        symbols = result['data']
        if not symbols:
            return

        log.info('扫描请求表: %d 只股票, 时间: %s' % (len(symbols), context.current_dt))

        # 2. 获取分钟数据
        records = []
        for symbol in symbols:
            try:
                bars = get_bars(symbol, count=2, unit='1m',
                               fields=['date', 'open', 'close', 'high', 'low', 'volume', 'money'],
                               include_now=True)

                if bars is None or len(bars) == 0:
                    continue

                bar = bars[-1]
                # 聚宽的 bar['date'] 已经是 datetime 类型
                dt = bar['date']

                records.append({
                    'symbol': symbol,
                    'trade_date': str(dt.date()),
                    'trade_time': str(dt.time()),
                    'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'open': float(bar['open']),
                    'close': float(bar['close']),
                    'high': float(bar['high']),
                    'low': float(bar['low']),
                    'volume': int(bar['volume']),
                    'money': float(bar['money'])
                })
                print(f"records is {records}")
            except Exception as e:
                log.error('获取 %s 数据失败: %s' % (symbol, str(e)))

        # 3. 发送到本地服务
        if records:
            resp = requests.post(SERVER_URL + '/save_minute',
                               json={'records': records}, timeout=REQUEST_TIMEOUT)
            result = resp.json()
            if result['code'] == 0:
                log.info('保存成功: %d 条' % result['count'])
            else:
                log.error('保存失败: ' + result.get('msg', ''))

    except Exception as e:
        log.error('执行失败: %s' % str(e))


def after_market_close(context):
    """收盘后运行"""
    log.info('收盘，更新最后收集时间')
    try:
        requests.post(SERVER_URL + '/update_collect_time', timeout=REQUEST_TIMEOUT)
    except Exception as e:
        log.error('更新失败: %s' % str(e))


# 因子列表
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


def export_factor_data(context):
    """导出因子数据并通过API保存"""

    # 1. 确定日期
    if EXPORT_DATE:
        end_date = EXPORT_DATE
    else:
        end_date = pd.Timestamp.today().strftime('%Y-%m-%d')

    print(f"导出日期: {end_date}")
    print(f"因子数量: {len(FACTOR_LIST)}")

    # 2. 获取股票池
    print("\n[1/4] 获取股票池...")
    # 获取前一个交易日（开盘前运行时，当天数据还没计算）
    if EXPORT_DATE:
        trade_date = get_trade_days(end_date=EXPORT_DATE, count=1)[0]
    else:
        # 开盘前运行，获取前一个有数据的交易日
        trade_dates = get_trade_days(end_date=pd.Timestamp.today().strftime('%Y-%m-%d'), count=2)
        trade_date = trade_dates[0]  # 取前一个交易日
    print(f"   trade_date={trade_date}")
    stock_list = get_index_stocks(INDEX_CODE, date=trade_date)
    print(f"   股票数量: {len(stock_list)}")

    # 3. 过滤股票
    print("\n[2/4] 过滤股票...")
    stock_list = filter_stocks(stock_list, trade_date)
    print(f"   过滤后数量: {len(stock_list)}")

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

        print(f"   批次 {batch_num}/{total_batches}: 处理 {len(batch_stocks)} 只股票...")

        try:
            # 获取因子数据
            batch_data = jqfactor.get_factor_values(
                securities=batch_stocks,
                factors=FACTOR_LIST,
                end_date=trade_date,
                count=1
            )

            # 处理并发送数据
            if batch_data is not None and len(batch_data) > 0:
                records = process_factor_data(batch_data, batch_stocks, FACTOR_LIST, trade_date, stock_name_map)

                # 发送到服务器
                if records:
                    # 打印前5条数据用于调试
                    if batch_num == 1:
                        print(f"      前5条数据预览:")
                        for idx, r in enumerate(records[:5]):
                            print(f"         [{idx+1}] {r['stock_code']} {r['stock_name']}: {len(r['factors'])} 个因子")
                    count = send_to_server(records)
                    total_count += count
                    print(f"      批次 {batch_num} 同步成功: {count} 条")
            else:
                print(f"      批次 {batch_num} 返回空数据")

        except Exception as e:
            print(f"      批次 {batch_num} 失败: {e}")
            import traceback
            traceback.print_exc()

        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"同步完成!")
    print(f"{'='*50}")
    print(f"交易日期: {trade_date}")
    print(f"同步记录数: {total_count}")

    return total_count


def process_factor_data(factor_result, stock_list, factor_list, trade_date, stock_name_map):
    """处理 jqfactor 返回的因子数据，转换为API所需格式"""

    records = []

    # 调试：打印返回数据结构
    # print(f"      factor_result 类型: {type(factor_result)}")
    # if isinstance(factor_result, dict):
    #     print(f"      factor_result keys: {list(factor_result.keys())[:3]}...")
    #     # first_key = list(factor_result.keys())[0]
        # first_df = factor_result[first_key]
        # print(f"      第一个因子 {first_key} 的数据:")
        # print(f"         类型: {type(first_df)}, shape: {first_df.shape if first_df is not None else 'None'}")
        # if first_df is not None and len(first_df) > 0:
        #     print(f"         columns: {first_df.columns.tolist()[:5]}...")
        #     print(f"         index: {first_df.index.tolist()}")
        #     print(f"         数据示例:\n{first_df}")

    if isinstance(factor_result, dict):
        # 字典格式：{因子名: DataFrame(日期x股票)}
        for stock in stock_list:
            factors = {}
            for factor_name, factor_df in factor_result.items():
                if factor_df is not None and len(factor_df) > 0:
                    values = factor_df.iloc[-1] if len(factor_df) > 1 else factor_df.iloc[0]
                    if stock in values.index:
                        val = values[stock]
                        # 转换NaN为None
                        factors[factor_name] = None if pd.isna(val) else float(val)

            if factors:  # 只保存有数据的股票
                records.append({
                    'trade_date': str(trade_date),
                    'stock_code': stock,
                    'stock_name': stock_name_map.get(stock, ''),
                    'factors': factors
                })

    elif isinstance(factor_result, pd.DataFrame):
        if isinstance(factor_result.columns, pd.MultiIndex):
            for stock in stock_list:
                factors = {}
                for factor in factor_list:
                    try:
                        val = factor_result.loc[:, (stock, factor)].iloc[-1]
                        factors[factor] = None if pd.isna(val) else float(val)
                    except:
                        factors[factor] = None

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
        resp = requests.post(
            SERVER_URL + '/save_factors_batch',
            json={'records': records},
            timeout=REQUEST_TIMEOUT
        )
        result = resp.json()
        if result['code'] == 0:
            return result['count']
        else:
            print(f"      服务器错误: {result.get('msg', '')}")
            return 0
    except Exception as e:
        print(f"      发送失败: {e}")
        return 0


def filter_stocks(stock_list, date):
    """过滤股票"""
    all_securities = get_all_securities(date=date)

    # 获取当日价格数据
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

        # 排除科创板、北交所
        if code.startswith(('68', '4', '8')):
            continue

        if stock not in all_securities.index:
            continue

        stock_info = all_securities.loc[stock]

        # 排除ST
        if 'ST' in stock_info.display_name or '*' in stock_info.display_name:
            continue

        # 排除退市
        if '退' in stock_info.display_name:
            continue

        # 排除涨跌停
        if stock in limit_dict:
            info = limit_dict[stock]
            if info['close'] >= info['high_limit'] or info['close'] <= info['low_limit']:
                continue

        filtered.append(stock)

    return filtered


# 运行
# df = export_factor_data()



