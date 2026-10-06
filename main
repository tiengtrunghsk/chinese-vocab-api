# -*- coding: utf-8 -*-
"""Chinese Vocab Analysis API — có AI mnemonics + tự động reload"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pypinyin import pinyin, Style
import os
import re
import sys
import json
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HAS_VOCAB = False
try:
    from vocab_data.radical_analyzer import (
        analyze_word, _split_components, get_radical_for_word
    )
    from vocab_data.mnemonic_generator import (
        generate_mnemonic, find_similar_chars
    )
    HAS_VOCAB = True
    print("[VocabAPI] vocab_data loaded OK")
except Exception as e:
    print("[VocabAPI] vocab_data load failed: " + str(e))


# ═══════════════════════════════════════════════════════════════
#  ⭐ AI MNEMONICS — LOAD + TỰ ĐỘNG RELOAD KHI FILE ĐỔI
# ═══════════════════════════════════════════════════════════════
_AI_MNEMONICS = {}          # Dict gốc từ file JSON
_AI_MNEMONICS_INDEX = {}    # Index zh → mnemonic (để lookup nhanh)
_AI_MNEMONICS_PATH = None   # Đường dẫn file đã load
_AI_MNEMONICS_MTIME = 0     # Lần cuối file thay đổi
_AI_MNEMONICS_LOADED = False


def _find_ai_mnemonics_file():
    """Tìm file ai_mnemonics.json ở các vị trí có thể."""
    here = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(here)
    candidates = [
        os.path.join(here, "data", "ai_mnemonics.json"),
        os.path.join(parent, "data", "ai_mnemonics.json"),
        os.path.join(os.getcwd(), "data", "ai_mnemonics.json"),
        "data/ai_mnemonics.json",
        os.path.join(here, "ai_mnemonics.json"),
        "ai_mnemonics.json",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _build_ai_index(data):
    """Build index zh → mnemonic từ dict gốc (key format: HSK|stt|zh)."""
    idx = {}
    for k, v in data.items():
        parts = k.split("|")
        if len(parts) != 3:
            continue
        zh = parts[2].strip()
        if not zh:
            continue
        # Ưu tiên HSK thấp (entry đầu tiên gặp)
        if zh not in idx:
            idx[zh] = v
    return idx


def _do_load_ai_mnemonics():
    """
    Đọc file + build index. Trả về True/False.
    Gọi khi:
      - Server khởi động
      - File bị thay đổi (mtime)
      - Endpoint /reload được gọi
    """
    global _AI_MNEMONICS, _AI_MNEMONICS_INDEX
    global _AI_MNEMONICS_PATH, _AI_MNEMONICS_MTIME, _AI_MNEMONICS_LOADED

    path = _find_ai_mnemonics_file()
    if not path:
        _AI_MNEMONICS = {}
        _AI_MNEMONICS_INDEX = {}
        _AI_MNEMONICS_PATH = None
        _AI_MNEMONICS_MTIME = 0
        _AI_MNEMONICS_LOADED = True
        print("[VocabAPI] [INFO] Khong co ai_mnemonics.json - dung meo tinh")
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            print("[VocabAPI] [WARN] ai_mnemonics.json khong phai dict")
            return False

        _AI_MNEMONICS = data
        _AI_MNEMONICS_INDEX = _build_ai_index(data)
        _AI_MNEMONICS_PATH = path
        _AI_MNEMONICS_MTIME = os.path.getmtime(path)
        _AI_MNEMONICS_LOADED = True

        print("[VocabAPI] [OK] Load " + str(len(data))
              + " meo nho AI tu: " + path)
        print("[VocabAPI] [OK] Index: " + str(len(_AI_MNEMONICS_INDEX)) + " chu")
        return True
    except Exception as e:
        print("[VocabAPI] [WARN] Loi doc ai_mnemonics.json: " + str(e))
        return False


def load_ai_mnemonics():
    """Load lần đầu khi server khởi động."""
    _do_load_ai_mnemonics()


def _check_ai_mnemonics_fresh():
    """
    ⭐ Kiểm tra mtime mỗi khi gọi get_ai_mnemonic.
    Nếu file mới hơn → tự động reload.
    ⭐ Nhanh (chỉ os.stat) — không đọc file nếu không có gì đổi.
    """
    if not _AI_MNEMONICS_LOADED:
        _do_load_ai_mnemonics()
        return

    path = _AI_MNEMONICS_PATH

    # Trường hợp 1: chưa có file nào được load
    if not path:
        new_path = _find_ai_mnemonics_file()
        if new_path:
            print("[VocabAPI] [NEW] File xuat hien: " + new_path)
            _do_load_ai_mnemonics()
        return

    # Trường hợp 2: file đã load nhưng bị xóa
    if not os.path.exists(path):
        print("[VocabAPI] [DELETED] File bi xoa: " + path)
        _do_load_ai_mnemonics()
        return

    # Trường hợp 3: file tồn tại — check mtime
    try:
        current_mtime = os.path.getmtime(path)
        if current_mtime > _AI_MNEMONICS_MTIME:
            print("[VocabAPI] [RELOAD] File thay doi, reload lai...")
            _do_load_ai_mnemonics()
    except Exception:
        pass


def get_ai_mnemonic(char):
    """Lấy mẹo nhớ AI cho 1 chữ Hán. Tự động reload nếu file đổi."""
    _check_ai_mnemonics_fresh()

    if not _AI_MNEMONICS_INDEX:
        return ""

    char = str(char or "").strip()
    if not char:
        return ""

    return _AI_MNEMONICS_INDEX.get(char, "")


app = Flask(__name__)
CORS(app)

# ⭐ Load AI mnemonics 1 lần khi khởi động
load_ai_mnemonics()


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════
def get_pinyin(char):
    if not char:
        return ''
    try:
        result = pinyin(char, style=Style.TONE)
        if result and result[0]:
            return result[0][0]
    except Exception:
        pass
    return ''


def parse_similar_diff(diff_text):
    result = {}
    if not diff_text:
        return result
    parts = [p.strip() for p in diff_text.split(';')]
    for p in parts:
        if '=' not in p:
            continue
        ch_part, rest = p.split('=', 1)
        ch_part = ch_part.strip()
        if len(ch_part) != 1:
            continue
        if not ('\u4e00' <= ch_part <= '\u9fff'):
            continue
        meaning = rest.strip()
        breakdown = ''
        m = re.match(r'^([^(]+?)\s*\(([^)]+)\)\s*$', rest.strip())
        if m:
            meaning = m.group(1).strip()
            breakdown = m.group(2).strip()
        else:
            meaning = rest.strip()
        result[ch_part] = {
            'meaning': meaning,
            'breakdown': breakdown,
        }
    return result


def strip_similar_from_mnemonic(mnemonic):
    if not mnemonic:
        return mnemonic
    markers = ['\n🔍', '\n📌', '\n\n🔍', '\n\n📌']
    cut_idx = len(mnemonic)
    for marker in markers:
        idx = mnemonic.find(marker)
        if idx != -1 and idx < cut_idx:
            cut_idx = idx
    return mnemonic[:cut_idx].rstrip()


def analyze_char(char):
    if not char or len(char) != 1:
        return None
    if not ('\u4e00' <= char <= '\u9fff'):
        return None
    if not HAS_VOCAB:
        return None
    try:
        result = {'char': char, 'pinyin': get_pinyin(char)}

        main_rad = get_radical_for_word(char)
        if main_rad:
            result['radical'] = {
                'zh': main_rad.get('zh', ''),
                'pinyin': main_rad.get('pinyin', ''),
                'meaning': main_rad.get('meaning', ''),
                'strokes': main_rad.get('strokes', 0),
                'position': main_rad.get('position', ''),
            }

        comps = _split_components(char)
        if comps:
            result['components'] = []
            for c in comps[:8]:
                result['components'].append({
                    'zh': c.get('zh', ''),
                    'pinyin': c.get('pinyin', ''),
                    'meaning': c.get('meaning', ''),
                    'position': c.get('position', ''),
                })

        # ⭐ CHỈ SỬA CHỖ NÀY: Ưu tiên AI, không có thì fallback y như cũ
        mnemonic = get_ai_mnemonic(char)
        if not mnemonic:
            mnemonic = generate_mnemonic(char)

        if mnemonic:
            mnemonic = strip_similar_from_mnemonic(mnemonic)
            result['mnemonic'] = mnemonic

        similar = find_similar_chars(char)
        if similar:
            sim_list = similar.get('similar') or []
            diff = similar.get('diff') or ''
            parsed = parse_similar_diff(diff)
            similar_full = []
            for ch in sim_list:
                ch = str(ch).strip()
                if not ch or len(ch) != 1:
                    continue
                info = parsed.get(ch, {})
                similar_full.append({
                    'char': ch,
                    'pinyin': get_pinyin(ch),
                    'meaning': info.get('meaning', ''),
                    'breakdown': info.get('breakdown', ''),
                })
            result['similar'] = {
                'list': similar_full,
                'diff': diff,
            }

        return result
    except Exception as e:
        print("[VocabAPI] analyze error '" + str(char) + "': " + str(e))
        return None


# ═══════════════════════════════════════════════════════════════
#  HTML HELPER — giữ nguyên như bản gốc
# ═══════════════════════════════════════════════════════════════
def render_test_page(ch):
    """Render trang /test — tách riêng để bọc try/except."""
    if not ch:
        return '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Test Vocab API</title>
<style>
body{font-family:-apple-system,sans-serif;max-width:700px;margin:40px auto;padding:0 20px;background:#f9fafb;color:#111827;line-height:1.5}
h1{color:#4f46e5;font-size:1.5rem}
input{padding:10px 14px;font-size:16px;border:2px solid #ccc;border-radius:8px;width:200px}
button{padding:10px 20px;font-size:16px;background:#4f46e5;color:#fff;border:none;border-radius:8px;cursor:pointer}
.hint{color:#666;font-size:14px;margin-top:10px}
.example{display:inline-block;margin:4px;padding:8px 14px;background:#f3f4f6;border-radius:6px;cursor:pointer;font-size:18px}
.example:hover{background:#e5e7eb}
a{color:#4f46e5}
</style>
</head>
<body>
<h1>🔍 Chinese Vocab API Test</h1>
<p>Nhập 1 chữ Hán để phân tích:</p>
<form method="GET" action="/test">
<input type="text" name="char" placeholder="VD: 权" maxlength="1" autofocus>
<button type="submit">Phân tích</button>
</form>
<p class="hint">Hoặc bấm thử:</p>
<div>
<span class="example" onclick="go('权')">权</span>
<span class="example" onclick="go('管')">管</span>
<span class="example" onclick="go('你')">你</span>
<span class="example" onclick="go('爱')">爱</span>
<span class="example" onclick="go('想')">想</span>
<span class="example" onclick="go('很')">很</span>
<span class="example" onclick="go('天')">天</span>
<span class="example" onclick="go('妈')">妈</span>
</div>
<script>function go(c){document.querySelector('input').value=c;document.querySelector('form').submit();}</script>
<hr style="margin:30px 0">
<p class="hint">Endpoints: <a href="/health">/health</a> — <a href="/debug?char=爱">/debug</a></p>
</body>
</html>'''

    if len(ch) != 1:
        return '<h1>Chỉ nhập 1 ký tự</h1><p><a href="/test">← Quay lại</a></p>'

    result = analyze_char(ch)

    if not result:
        return '<h1>❌ Không phân tích được: ' + ch + '</h1><p><a href="/test">← Thử chữ khác</a></p>'

    rad = result.get('radical') or {}
    comps = result.get('components') or []
    mnemonic = result.get('mnemonic') or '(Chưa có mẹo nhớ)'
    similar = result.get('similar') or {}
    pinyin_str = result.get('pinyin') or ''

    comps_html = ''
    for c in comps:
        comps_html += (
            '<div class="comp-item">'
            '<span class="comp-char">' + (c.get('zh') or '') + '</span>'
            '<span class="comp-py">' + (c.get('pinyin') or '') + '</span>'
            '<span class="comp-meaning">' + (c.get('meaning') or '') + '</span>'
            '</div>'
        )
    if not comps_html:
        comps_html = '<p style="color:#999">Không có dữ liệu</p>'

    if rad:
        rad_html = (
            '<div class="radical-box">'
            '<span class="rad-char">' + (rad.get('zh') or '') + '</span>'
            '<span class="rad-name">Bộ ' + (rad.get('pinyin') or '') + '</span>'
            '<span class="rad-meaning">' + (rad.get('meaning') or '') + '</span>'
            '</div>'
        )
    else:
        rad_html = '<p style="color:#999">Không xác định</p>'

    similar_html = ''
    sim_list = similar.get('list') or []
    if sim_list:
        cards_html = ''
        for item in sim_list:
            c = item.get('char', '')
            py = item.get('pinyin', '')
            vi = item.get('meaning', '')
            bd = item.get('breakdown', '')
            cards_html += (
                '<div class="similar-card">'
                '<div class="sim-char">' + c + '</div>'
                '<div class="sim-py">' + py + '</div>'
                '<div class="sim-vi">' + vi + '</div>'
                '<div class="sim-bd">' + bd + '</div>'
                '</div>'
            )
        similar_html = (
            '<div class="similar-box">'
            '<div class="similar-title">🔍 Dễ nhầm</div>'
            '<div class="similar-cards">' + cards_html + '</div>'
            '</div>'
        )

    mnem_esc = (mnemonic
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('\n', '<br>'))

    return '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Phân tích: ''' + ch + '''</title>
<style>
body{font-family:-apple-system,sans-serif;max-width:700px;margin:30px auto;padding:0 20px;background:#f9fafb;color:#111827;line-height:1.5}
h1{color:#4f46e5;font-size:1.3rem}
.main-char{font-size:5rem;font-weight:700;text-align:center;font-family:"PingFang SC","Microsoft YaHei",sans-serif;margin:1rem 0 .25rem;line-height:1}
.main-pinyin{text-align:center;font-size:1.3rem;font-style:italic;color:#6b7280;margin-bottom:1.5rem}
.section{background:#fff;border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.section-title{font-size:.8rem;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#6b7280;margin-bottom:.75rem}
.radical-box{display:flex;align-items:center;gap:.75rem;flex-wrap:wrap}
.rad-char{font-size:2.5rem;font-weight:700;font-family:"PingFang SC",sans-serif;color:#1d4ed8;line-height:1}
.rad-name{font-size:1rem;font-weight:700;color:#1d4ed8;background:#dbeafe;padding:.25rem .6rem;border-radius:6px}
.rad-meaning{font-size:.95rem;color:#374151}
.comp-item{display:flex;align-items:center;gap:.75rem;padding:.6rem .75rem;border-radius:8px;background:#f9fafb;margin-bottom:.5rem}
.comp-item:last-child{margin-bottom:0}
.comp-char{font-size:1.75rem;font-weight:700;min-width:1.5em;font-family:"PingFang SC",sans-serif;line-height:1}
.comp-py{font-size:.85rem;font-style:italic;color:#6b7280;min-width:4em}
.comp-meaning{font-size:.9rem;color:#374151;flex:1}
.mnemonic-box{background:#fffbeb;border-left:4px solid #f59e0b;padding:.85rem 1rem;border-radius:8px;font-size:.95rem;color:#78350f;line-height:1.7}
.similar-box{background:#fef2f2;border-left:4px solid #ef4444;padding:.85rem 1rem;border-radius:8px;margin-top:.75rem}
.similar-title{font-weight:700;color:#b91c1c;font-size:.9rem;margin-bottom:.6rem}
.similar-cards{display:flex;gap:.6rem;flex-wrap:wrap}
.similar-card{display:flex;flex-direction:column;align-items:center;min-width:80px;padding:.65rem .75rem;background:#fff;border:2px solid #fecaca;border-radius:10px}
.sim-char{font-size:2rem;font-weight:700;font-family:"PingFang SC",sans-serif;line-height:1;margin-bottom:.3rem}
.sim-py{font-size:.8rem;font-style:italic;color:#6b7280;margin-bottom:.25rem}
.sim-vi{font-size:.78rem;color:#b91c1c;font-weight:700;text-align:center;margin-bottom:.2rem}
.sim-bd{font-size:.65rem;color:#9ca3af;text-align:center;font-family:"PingFang SC",sans-serif;line-height:1.3;padding-top:.2rem;border-top:1px dashed #e5e7eb;margin-top:.2rem;width:100%}
.back-btn{display:inline-block;margin-top:1rem;padding:.6rem 1.2rem;background:#4f46e5;color:#fff;border-radius:8px;font-weight:600;text-decoration:none}
</style>
</head>
<body>
<h1>🔍 Kết quả phân tích</h1>
<div class="main-char">''' + ch + '''</div>
<div class="main-pinyin">''' + pinyin_str + '''</div>
<div class="section">
<div class="section-title">Bộ thủ chính</div>
''' + rad_html + '''
</div>
<div class="section">
<div class="section-title">Thành phần cấu tạo</div>
''' + comps_html + '''
</div>
<div class="section">
<div class="section-title">Mẹo nhớ</div>
<div class="mnemonic-box">''' + mnem_esc + '''</div>
''' + similar_html + '''
</div>
<a href="/test" class="back-btn">← Phân tích chữ khác</a>
</body>
</html>'''


# ═══════════════════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════════════════
@app.route('/health')
def health():
    return jsonify({
        'ok': True,
        'has_vocab': HAS_VOCAB,
        'ai_mnemonics_loaded': len(_AI_MNEMONICS),
        'ai_index_size': len(_AI_MNEMONICS_INDEX),
        'ai_file_path': _AI_MNEMONICS_PATH,
        'ai_file_mtime': _AI_MNEMONICS_MTIME,
        'version': '1.5',
    })


@app.route('/reload', methods=['POST', 'GET'])
def reload_ai():
    """
    ⭐ Force reload ai_mnemonics.json mà không cần restart server.
    Gọi: POST /reload  hoặc  GET /reload
    """
    ok = _do_load_ai_mnemonics()
    return jsonify({
        'ok': ok,
        'count': len(_AI_MNEMONICS),
        'index_size': len(_AI_MNEMONICS_INDEX),
        'path': _AI_MNEMONICS_PATH,
        'mtime': _AI_MNEMONICS_MTIME,
    })


@app.route('/debug')
def debug():
    try:
        ch = request.args.get('char', '').strip()
        if not ch:
            return jsonify({'error': 'Missing ?char=...'})
        similar_raw = None
        diff_text = ''
        parsed = {}
        mnemonic_raw = ''
        mnemonic_stripped = ''
        ai_mnemonic = ''
        static_mnemonic = ''
        error = None
        try:
            similar_raw = find_similar_chars(ch)
            if similar_raw:
                diff_text = similar_raw.get('diff', '')
                parsed = parse_similar_diff(diff_text)

            # Lấy cả 2 nguồn để so sánh
            ai_mnemonic = get_ai_mnemonic(ch) or ''
            static_mnemonic = generate_mnemonic(ch) or ''

            mnemonic_raw = ai_mnemonic if ai_mnemonic else static_mnemonic
            mnemonic_stripped = strip_similar_from_mnemonic(mnemonic_raw)
        except Exception as e:
            error = str(e)
        return jsonify({
            'char': ch,
            'has_vocab': HAS_VOCAB,
            'error': error,
            'similar_raw': similar_raw,
            'diff_text': diff_text,
            'parsed': parsed,
            'mnemonic_ai': ai_mnemonic,
            'mnemonic_static': static_mnemonic,
            'mnemonic_raw': mnemonic_raw,
            'mnemonic_stripped': mnemonic_stripped,
            'ai_count': len(_AI_MNEMONICS),
            'ai_index_size': len(_AI_MNEMONICS_INDEX),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json(force=True, silent=True) or {}
        char = data.get('char', '').strip()
        if not char:
            return jsonify({'ok': False, 'error': 'Missing char'}), 400
        if len(char) != 1:
            return jsonify({'ok': False, 'error': 'Only 1 char'}), 400
        result = analyze_char(char)
        if not result:
            return jsonify({
                'ok': False, 'error': 'Analysis failed', 'char': char
            }), 500
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/analyze_batch', methods=['POST'])
def analyze_batch():
    try:
        data = request.get_json(force=True, silent=True) or {}
        chars = data.get('chars', [])
        if not isinstance(chars, list):
            return jsonify({'ok': False, 'error': 'chars must be array'}), 400
        if len(chars) > 20:
            return jsonify({'ok': False, 'error': 'Max 20 chars'}), 400
        result = {}
        for ch in chars:
            ch = str(ch).strip()
            if not ch or len(ch) != 1:
                continue
            if ch in result:
                continue
            analysis = analyze_char(ch)
            if analysis:
                result[ch] = analysis
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/test')
def test_get():
    try:
        ch = request.args.get('char', '').strip()
        html = render_test_page(ch)
        return html
    except Exception:
        tb = traceback.format_exc()
        return (
            '<pre style="background:#fee;padding:20px;border-radius:8px;'
            'overflow:auto;font-size:12px">' + tb + '</pre>'
        ), 500


@app.route('/')
def index():
    return jsonify({
        'name': 'Chinese Vocab Analysis API',
        'version': '1.5',
        'ai_mnemonics_loaded': len(_AI_MNEMONICS),
        'ai_index_size': len(_AI_MNEMONICS_INDEX),
        'endpoints': {
            'health': 'GET /health',
            'reload': 'POST /reload  (force reload ai_mnemonics.json)',
            'test': 'GET /test?char=权',
            'debug': 'GET /debug?char=爱',
            'analyze': 'POST /analyze  { char: "权" }',
            'analyze_batch': 'POST /analyze_batch  { chars: ["权"] }',
        }
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
