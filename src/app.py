import os
import pymysql

from flask import Flask, request, jsonify, render_template
from models.models import db, StrategyPosition, InternalPassword
from config import SQLALCHEMY_DATABASE_URI, API_HOST, API_PORT, CRYPTO_AUTH_CONFIG, DB_CONFIG
from auth.simple_crypto_auth import SimpleCryptoAuth, require_auth
import auth.simple_crypto_auth as auth_module
from functools import wraps
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    # 初始化认证系统
    init_auth_system()
    
    with app.app_context():
        db.create_all()
    
    return app

def init_auth_system():
    """初始化认证系统"""
    if CRYPTO_AUTH_CONFIG.get('ENABLED', True):
        # 启用加密认证
        try:
            # 优先使用文件路径配置
            if 'PRIVATE_KEY_FILE' in CRYPTO_AUTH_CONFIG and 'PUBLIC_KEY_FILE' in CRYPTO_AUTH_CONFIG:
                private_key_file = CRYPTO_AUTH_CONFIG['PRIVATE_KEY_FILE']
                public_key_file = CRYPTO_AUTH_CONFIG['PUBLIC_KEY_FILE']
                
                # 设置全局认证实例（从文件读取）
                auth_module.crypto_auth = SimpleCryptoAuth(
                    private_key_file=private_key_file,
                    public_key_file=public_key_file
                )
                print(f"加密认证系统已启用（从文件读取密钥: {private_key_file}, {public_key_file}）")
            
            # 兼容旧的字符串配置方式
            elif 'PRIVATE_KEY' in CRYPTO_AUTH_CONFIG and 'PUBLIC_KEY' in CRYPTO_AUTH_CONFIG:
                private_key = CRYPTO_AUTH_CONFIG['PRIVATE_KEY']
                public_key = CRYPTO_AUTH_CONFIG['PUBLIC_KEY']
                
                # 设置全局认证实例（从字符串读取）
                auth_module.crypto_auth = SimpleCryptoAuth(private_key, public_key)
                print("加密认证系统已启用（从配置字符串读取密钥）")
            
            else:
                raise ValueError("密钥配置不完整，请配置密钥文件路径或密钥字符串")
                
        except Exception as e:
            print(f"加密认证系统初始化失败: {e}")
            print("请检查密钥文件是否存在或密钥格式是否正确")
            raise
    else:
        # 禁用加密认证，使用简单API密钥
        print("加密认证已禁用，使用简单API密钥认证")
        if not CRYPTO_AUTH_CONFIG.get('SIMPLE_API_KEY'):
            print("警告: 未配置简单API密钥，API将不安全！")

def require_internal_password(f):
    """内部API密码验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取密码
        password = None
        
        # 尝试从请求头获取密码
        if 'X-Internal-Password' in request.headers:
            password = request.headers['X-Internal-Password']
        # 尝试从请求体获取密码
        elif request.is_json and request.get_json():
            data = request.get_json()
            password = data.get('internal_password')
        # 尝试从表单数据获取密码
        elif request.form:
            password = request.form.get('internal_password')
        
        if not password:
            return jsonify({
                'error': '缺少内部密码',
                'message': '请在请求头X-Internal-Password或请求体internal_password字段中提供密码'
            }), 401
        
        # 验证密码
        if not InternalPassword.verify_password(password):
            return jsonify({
                'error': '密码验证失败',
                'message': '内部密码不正确'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function

app = create_app()

# MySQL直接连接（用于分钟数据和因子数据）
def get_db():
    """获取数据库连接"""
    return pymysql.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['username'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        charset='utf8mb4'
    )

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


# ==================== 聚宽数据收集接口 ====================

@app.route('/api/v1/jq/health', methods=['GET'])
def jq_health():
    """聚宽服务健康检查"""
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})


@app.route('/api/v1/jq/get_symbols', methods=['GET'])
@require_auth
def jq_get_symbols():
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


@app.route('/api/v1/jq/save_minute', methods=['POST'])
@require_auth
def jq_save_minute():
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


@app.route('/api/v1/jq/update_collect_time', methods=['POST'])
@require_auth
def jq_update_collect_time():
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


@app.route('/api/v1/jq/save_factors', methods=['POST'])
@require_auth
def jq_save_factors():
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


@app.route('/api/v1/jq/save_factors_batch', methods=['POST'])
@require_auth
def jq_save_factors_batch():
    """批量保存因子数据"""
    try:
        data = request.json
        records = data.get('records', [])
        print(f"[save_factors_batch] 收到 {len(records)} 条记录")

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
        print(f"[save_factors_batch] 写入成功 {count} 条")
        cursor.close()
        conn.close()
        return jsonify({'code': 0, 'count': count})
    except Exception as e:
        print(f"[save_factors_batch] 错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'code': -1, 'msg': str(e)})

@app.route('/api/v1/positions/update', methods=['POST'])
@require_auth  # 使用统一认证装饰器
def update_positions():
    try:
        data = request.get_json()
        if not data or 'strategy_name' not in data or 'positions' not in data:
            return jsonify({'error': '无效的数据格式'}), 400
            
        StrategyPosition.update_positions(data['strategy_name'], data['positions'])
        return jsonify({
            'message': '持仓更新成功',
            'client_id': getattr(request, 'client_id', 'unknown'),
            'auth_type': getattr(request, 'auth_type', 'unknown')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/positions/update/internal', methods=['POST'])
@require_internal_password  # 使用内部密码验证
def update_positions_internal():
    """内部持仓更新接口，使用密码验证而不是RSA验证"""
    try:
        data = request.get_json()
        if not data or 'strategy_name' not in data or 'positions' not in data:
            return jsonify({'error': '无效的数据格式'}), 400
            
        StrategyPosition.update_positions(data['strategy_name'], data['positions'])
        return jsonify({
            'message': '持仓更新成功（内部接口）',
            'strategy_name': data['strategy_name'],
            'positions_count': len(data['positions']),
            'auth_type': 'internal_password'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/auth/info', methods=['GET'])
def get_auth_info():
    """获取认证系统信息"""
    return jsonify({
        'crypto_enabled': CRYPTO_AUTH_CONFIG.get('ENABLED', True),
        'auth_type': 'crypto' if CRYPTO_AUTH_CONFIG.get('ENABLED', True) else 'simple',
        'public_key': CRYPTO_AUTH_CONFIG['PUBLIC_KEY'] if CRYPTO_AUTH_CONFIG.get('ENABLED', True) else None,
        'algorithm': 'RSA-2048' if CRYPTO_AUTH_CONFIG.get('ENABLED', True) else 'API-Key',
        'internal_password_info': InternalPassword.get_current_password_info()
    })

@app.route('/api/v1/internal/password/info', methods=['GET'])
def get_internal_password_info():
    """获取内部密码信息"""
    return jsonify(InternalPassword.get_current_password_info())

@app.route('/api/v1/internal/password/set', methods=['POST'])
@require_internal_password
def set_internal_password():
    """设置内部密码（需要当前密码验证）"""
    try:
        data = request.get_json()
        if not data or 'new_password' not in data:
            return jsonify({'error': '缺少新密码'}), 400
        
        new_password = data['new_password']
        if len(new_password) < 6:
            return jsonify({'error': '密码长度至少6位'}), 400
        
        InternalPassword.set_password(new_password)
        return jsonify({
            'message': '密码设置成功',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/positions/strategy/<strategy_name>', methods=['GET'])
def get_strategy_positions(strategy_name):
    try:
        strategy = StrategyPosition.query.filter_by(strategy_name=strategy_name).first()
        if strategy:
            return jsonify({
                'positions': [{
                    'code': position['code'],
                    'name': position.get('name', ""),
                    'volume': position['volume'],
                    'cost': position['cost']
                } for position in strategy.positions],
                'update_time': strategy.update_time.strftime('%Y-%m-%d %H:%M:%S') if strategy.update_time else None
            })
        else:
            return jsonify({
                'positions': [],
                'update_time': None
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/positions/total', methods=['GET'])
def get_total_positions():
    try:
        strategy_names_str = request.args.get('strategies')
        strategy_names = strategy_names_str.split(',') if strategy_names_str else None
        
        # 是否包含调整策略，默认包含
        include_adjustments = request.args.get('include_adjustments', 'true').lower() == 'true'
        
        result = StrategyPosition.get_total_positions(strategy_names, include_adjustments)
        return jsonify({
            'positions': result['positions'],
            'update_time': result['update_time'].strftime('%Y-%m-%d %H:%M:%S') if result['update_time'] else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/positions/all', methods=['GET'])
def get_all_positions():
    try:
        positions = StrategyPosition.get_all_strategy_positions()
        return jsonify({
            'strategies': [{
                'strategy_name': item['strategy_name'],
                'positions': [{
                    'code': pos['code'],
                    'name': pos.get('name', ""),
                    'volume': pos['volume'],
                    'cost': pos['cost']
                } for pos in item['positions']],
                'update_time': item['update_time'].strftime('%Y-%m-%d %H:%M:%S')
            } for item in positions]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/adjustment')
def adjustment():
    return render_template('adjustment.html')

@app.route('/password')
def password_management():
    return render_template('password.html')

if __name__ == '__main__':
    app.run(
        host=API_HOST,
        port=API_PORT,
        debug=True
    )