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

# 你的本地服务地址（需要公网IP或内网穿透）
SERVER_URL = 'http://你的服务器IP:5366'
REQUEST_TIMEOUT = 10


def initialize(context):
    """初始化函数"""
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    log.info('分钟数据收集服务启动')

    # 每分钟执行
    run_daily(collect_minute_data, time='every_bar', reference_security='000300.XSHG')


def is_trading_time(current_dt):
    """判断是否在交易时间"""
    current_time = current_dt.time()
    t = lambda s: datetime.strptime(s, '%H:%M').time()
    return (t('09:30') <= current_time <= t('11:30')) or \
           (t('13:00') <= current_time <= t('15:00'))


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
                dt = datetime.fromtimestamp(bar['date'] / 1000)

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
