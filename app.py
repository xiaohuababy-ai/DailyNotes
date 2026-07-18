from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import glob
from datetime import datetime
import hashlib
import time
import uuid  # ⬅️ 添加这一行
import requests  # ⬅️ 确保也有这一行（用于调用有道API）

app = Flask(__name__)
CORS(app)

# ====== 配置 ======
RECORDS_DIR = 'records'  # 记录存储文件夹

# 确保 records 文件夹存在
if not os.path.exists(RECORDS_DIR):
    os.makedirs(RECORDS_DIR)


# ================================================================
#  工具函数
# ================================================================

def get_record_file_path(record_id):
    """根据记录ID获取文件路径"""
    return os.path.join(RECORDS_DIR, f'{record_id}.json')


def save_record_to_file(record_id, data):
    """保存单条记录到文件"""
    file_path = get_record_file_path(record_id)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


def load_record_from_file(record_id):
    """从文件加载单条记录"""
    file_path = get_record_file_path(record_id)
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_all_record_ids():
    """获取所有记录ID列表"""
    pattern = os.path.join(RECORDS_DIR, '*.json')
    files = glob.glob(pattern)
    ids = []
    for f in files:
        basename = os.path.basename(f)
        record_id = basename.replace('.json', '')
        ids.append(record_id)
    return ids


def get_records_by_date(date_str):
    """获取指定日期的所有记录"""
    all_ids = get_all_record_ids()
    records = []
    for rid in all_ids:
        if rid.startswith(date_str):
            data = load_record_from_file(rid)
            if data:
                records.append(data)
    # 按时间排序（最新的在前）
    records.sort(key=lambda x: x.get('id', ''), reverse=True)
    return records


def get_days_with_records(year, month):
    """获取某个月份有记录的日期列表（返回日期数字列表）"""
    prefix = f'{year}-{str(month).zfill(2)}'
    all_ids = get_all_record_ids()
    days = set()
    for rid in all_ids:
        if rid.startswith(prefix):
            # rid 格式: 2026-07-21_143025
            day_str = rid.split('-')[2].split('_')[0]  # 提取日期数字
            try:
                day = int(day_str)
                days.add(day)
            except:
                pass
    return sorted(list(days))


# ================================================================
#  API 接口
# ================================================================



@app.route('/record/<record_id>', methods=['DELETE'])
def delete_record(record_id):
    try:
        file_path = get_record_file_path(record_id)
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': f'记录 {record_id} 不存在'}), 404
        os.remove(file_path)
        return jsonify({'success': True, 'id': record_id, 'message': '记录删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/')
def serve_html():
    """提供前端页面"""
    try:
        with open('dailynote.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '未找到 dailynote.html 文件，请确保它在同一目录下', 404


@app.route('/record', methods=['POST'])
def save_record():
    """
    保存记录
    Body: {
        "id": "2026-07-21_143025",
        "date": "2026-07-21",
        "words": ["apple", "banana"],
        "phrases": ["how are you"],
        "sentences": ["I love coding."]
    }
    """
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data or 'id' not in data:
            return jsonify({'success': False, 'error': '缺少记录ID'}), 400
        
        record_id = data['id']
        
        # 检查是否已存在
        if os.path.exists(get_record_file_path(record_id)):
            return jsonify({'success': False, 'error': f'记录 {record_id} 已存在'}), 409
        
        # 保存
        save_record_to_file(record_id, data)
        
        return jsonify({
            'success': True,
            'id': record_id,
            'message': '记录保存成功'
        })
        
    except Exception as e:
        print(f'保存记录失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/records', methods=['GET'])
def get_records():
    """
    获取指定日期的所有记录
    Query: ?date=2026-07-21
    """
    try:
        date_str = request.args.get('date')
        
        if not date_str:
            return jsonify({'success': False, 'error': '缺少日期参数'}), 400
        
        records = get_records_by_date(date_str)
        
        return jsonify({
            'success': True,
            'date': date_str,
            'count': len(records),
            'records': records
        })
        
    except Exception as e:
        print(f'获取记录失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/calendar', methods=['GET'])
def get_calendar():
    """
    获取某个月份有记录的日期列表
    Query: ?year=2026&month=7
    """
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        if not year or not month:
            return jsonify({'success': False, 'error': '缺少年份或月份参数'}), 400
        
        if month < 1 or month > 12:
            return jsonify({'success': False, 'error': '月份必须在 1-12 之间'}), 400
        
        days = get_days_with_records(year, month)
        
        return jsonify({
            'success': True,
            'year': year,
            'month': month,
            'days_with_records': days
        })
        
    except Exception as e:
        print(f'获取日历数据失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'service': 'dailynote'}), 200

@app.route('/record/<record_id>', methods=['PUT'])
def update_record(record_id):
    """
    更新已有记录（用于增删单词/短语/句子）
    """
    try:
        data = request.get_json()
        
        # 检查记录是否存在
        file_path = get_record_file_path(record_id)
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': f'记录 {record_id} 不存在'}), 404
        
        # 加载原有记录
        existing = load_record_from_file(record_id)
        if not existing:
            return jsonify({'success': False, 'error': '记录数据损坏'}), 500
        
        # 更新字段（只更新 words, phrases, sentences）
        if 'words' in data:
            existing['words'] = data['words']
        if 'phrases' in data:
            existing['phrases'] = data['phrases']
        if 'sentences' in data:
            existing['sentences'] = data['sentences']
        
         # 确保 review_time 字段存在
        if 'review_time' not in existing:
            existing['review_time'] = 0

        # 保存
        save_record_to_file(record_id, existing)
        
        return jsonify({
            'success': True,
            'id': record_id,
            'message': '记录更新成功'
        })
        
    except Exception as e:
        print(f'更新记录失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# 有道翻译 API 代理
# ================================================================

# ====== 请替换为你的有道智云应用信息 ======
APP_KEY = '413abe2e25fa0cbd';
APP_SECRET = 'ogqQhYIsceRsgyBFlPvPtjNMfFsefQxm';
# ========================================

# ⚠️ 请替换为你的有道智云应用信息
YOUDAO_APP_KEY = '413abe2e25fa0cbd';
YOUDAO_APP_SECRET = 'ogqQhYIsceRsgyBFlPvPtjNMfFsefQxm'


@app.route('/translate', methods=['GET', 'POST'])
def translate_api():
    """
    代理有道翻译 API
    默认翻译成中文（zh-CHS）
    """
    try:
        # 1. 获取参数
        if request.method == 'GET':
            q = request.args.get('q')
            from_lang = request.args.get('from', 'es')
        else:
            data = request.get_json() or {}
            q = data.get('q')
            from_lang = data.get('from', 'es')
            
        
        # 目标语言固定为中文
        to_lang = 'zh-CHS'
        
        if not q or q.strip() == '':
            return jsonify({'success': False, 'error': '缺少翻译文本'}), 400
        
        # 2. 生成签名参数
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        q_len = len(q)
        if q_len <= 20:
            input_text = q
        else:
            input_text = q[:10] + str(q_len) + q[-10:]
        
        sign_str = YOUDAO_APP_KEY + input_text + salt + curtime + YOUDAO_APP_SECRET
        sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
        
        # 3. 构建请求参数
        params = {
            'q': q,
            'from': from_lang,
            'to': to_lang,
            'appKey': YOUDAO_APP_KEY,
            'salt': salt,
            'sign': sign,
            'signType': 'v3',
            'curtime': curtime,
        }
        
        # 4. 调用有道 API
        response = requests.get(
            'https://openapi.youdao.com/api',
            params=params,
            timeout=10
        )
        result = response.json()
        
        # 5. 处理返回结果
        if result.get('errorCode') == '0':
            translation = result.get('translation', [])
            if translation and len(translation) > 0:
                return jsonify({
                    'success': True,
                    'translation': translation[0],
                    'query': result.get('query', q)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '翻译结果为空'
                })
        else:
            # 有道 API 错误
            error_code = result.get('errorCode')
            error_msg = {
                '101': '应用ID无效，请检查 YOUDAO_APP_KEY',
                '103': '签名错误，请检查 YOUDAO_APP_SECRET',
                '108': '请求频率超限，请稍后重试',
                '109': '请求IP不在白名单内',
                '202': '翻译文本过长',
                '207': '不支持的语种类型',
                '302': '翻译文本过长（超过限制）'
            }.get(error_code, f'有道API错误: {error_code}')
            
            return jsonify({
                'success': False,
                'error': error_msg,
                'errorCode': error_code
            }), 500
            
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': '翻译请求超时，请稍后重试'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': '网络连接失败，请检查网络'}), 503
    except Exception as e:
        print(f'翻译失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

# ================================================================
#  启动服务
# ================================================================

if __name__ == '__main__':
    print('=' * 50)
    print('📖 外语学习记录服务已启动')
    print('=' * 50)
    print(f'📁 数据存储目录: {os.path.abspath(RECORDS_DIR)}')
    print('🌐 访问地址: http://localhost:5005')
    print('=' * 50)
    app.run(debug=True, host='0.0.0.0', port=5005)