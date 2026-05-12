"""
本地Flask服务 - 接收聚宽发送的分钟数据并写入MySQL
运行方式: python src/server.py
"""

from flask import Flask, request, jsonify
import pymysql
from datetime import datetime
import os

app = Flask(__name__)

# MySQL连接配置 - 从环境变量读取或使用默认值
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '119.29.53.207'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', '!Q@W123456'),
    'database': os.getenv('MYSQL_DATABASE', 'test_db'),
    'charset': 'utf8mb4'
}


def get_db():
    """获取数据库连接"""
    return pymysql.connect(**MYSQL_CONFIG)


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})


@app.route('/get_symbols', methods=['GET'])
def get_symbols():
    """返回需要收集的股票列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT symbol FROM minute_data_request WHERE enabled = 1")
        symbols = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'code': 0, 'data': symbols})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


@app.route('/save_minute', methods=['POST'])
def save_minute():
    """保存分钟数据"""
    try:
        data = request.json
        records = data.get('records', [])

        if not records:
            return jsonify({'code': 0, 'count': 0})

        conn = get_db()
        cursor = conn.cursor()

        for r in records:
            sql = """
                INSERT INTO stock_minute_data
                (symbol, trade_date, trade_time, datetime, open, close, high, low, volume, money)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                open = VALUES(open), close = VALUES(close), high = VALUES(high),
                low = VALUES(low), volume = VALUES(volume), money = VALUES(money)
            """
            cursor.execute(sql, (
                r['symbol'], r['trade_date'], r['trade_time'], r['datetime'],
                r['open'], r['close'], r['high'], r['low'], r['volume'], r['money']
            ))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'code': 0, 'count': len(records)})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


@app.route('/update_collect_time', methods=['POST'])
def update_collect_time():
    """更新最后收集时间"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE minute_data_request
            SET last_collect_time = %s
            WHERE enabled = 1
        """, (datetime.now(),))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'code': 0})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


# 因子数据表字段列表
FACTOR_COLUMNS = [
    'cube_of_size', 'MFI14', 'Skewness20', 'financial_assets', 'bear_power',
    'PSY', 'Kurtosis120', 'VMACD', 'single_day_VPT', 'interest_free_current_liability',
    'BIAS60', 'ATR6', 'sales_to_price_ratio', 'cash_flow_to_price_ratio', 'Rank1M',
    'Kurtosis60', 'fifty_two_week_close_rank', 'arron_up_25', 'Kurtosis20',
    'daily_standard_deviation', 'Skewness60', 'single_day_VPT_12', 'earnings_yield',
    'leverage', 'CR20', 'VOSC', 'price_no_fq', 'Variance20', 'WVAD', 'ROC120',
    'money_flow_20', 'circulating_market_cap', 'book_to_price_ratio', 'MAWVAD',
    'ATR14', 'turnover_volatility', 'momentum', 'MASS', 'VEMA5', 'DAVOL5',
    'natural_log_of_market_cap', 'arron_down_25', 'VDIFF', 'liquidity'
]


@app.route('/save_factors', methods=['POST'])
def save_factors():
    """保存因子数据（宽表格式）"""
    try:
        data = request.json
        trade_date = data.get('trade_date')
        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name', '')
        factors = data.get('factors', {})

        if not trade_date or not stock_code:
            return jsonify({'code': -1, 'msg': '缺少 trade_date 或 stock_code'})

        conn = get_db()
        cursor = conn.cursor()

        # 构建动态SQL
        columns = ['trade_date', 'stock_code', 'stock_name'] + FACTOR_COLUMNS
        placeholders = ['%s'] * len(columns)
        update_parts = [f"{col} = VALUES({col})" for col in FACTOR_COLUMNS]

        values = [trade_date, stock_code, stock_name]
        for col in FACTOR_COLUMNS:
            values.append(factors.get(col))

        sql = f"""
            INSERT INTO factor_data ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON DUPLICATE KEY UPDATE
            stock_name = VALUES(stock_name),
            {', '.join(update_parts)}
        """

        cursor.execute(sql, values)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'code': 0, 'count': 1})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


@app.route('/save_factors_batch', methods=['POST'])
def save_factors_batch():
    """批量保存因子数据"""
    try:
        data = request.json
        records = data.get('records', [])

        if not records:
            return jsonify({'code': 0, 'count': 0})

        conn = get_db()
        cursor = conn.cursor()

        count = 0
        for r in records:
            trade_date = r.get('trade_date')
            stock_code = r.get('stock_code')
            stock_name = r.get('stock_name', '')
            factors = r.get('factors', {})

            if not trade_date or not stock_code:
                continue

            columns = ['trade_date', 'stock_code', 'stock_name'] + FACTOR_COLUMNS
            placeholders = ['%s'] * len(columns)
            update_parts = [f"{col} = VALUES({col})" for col in FACTOR_COLUMNS]

            values = [trade_date, stock_code, stock_name]
            for col in FACTOR_COLUMNS:
                values.append(factors.get(col))

            sql = f"""
                INSERT INTO factor_data ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                ON DUPLICATE KEY UPDATE
                stock_name = VALUES(stock_name),
                {', '.join(update_parts)}
            """

            cursor.execute(sql, values)
            count += 1

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'code': 0, 'count': count})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


if __name__ == '__main__':
    port = int(os.getenv('SERVER_PORT', 5000))
    print(f'服务启动在端口 {port}')
    app.run(host='0.0.0.0', port=port, debug=False)
