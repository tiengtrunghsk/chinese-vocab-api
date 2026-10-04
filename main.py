# -*- coding: utf-8 -*-
"""
Chinese Vocab Analysis API
- POST /analyze       { "char": "权" }
- POST /analyze_batch { "chars": ["权", "管"] }
- GET  /test?char=权  — test bằng trình duyệt
- GET  /health
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pypinyin import pinyin, Style

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from vocab_data.radical_analyzer import (
        analyze_word,
        _split_components,
        get_radical_for_word,
        find_components,
    )
    from vocab_data.mnemonic_generator import (
        generate_mnemonic,
        find_similar_chars,
    )
    HAS_VOCAB = True
    print("[VocabAPI] vocab_data loaded OK")
except Exception as e:
    HAS_VOCAB = False
    print("[VocabAPI] vocab_data load failed: " + str(e))


app = Flask(__name__)
CORS(app)


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


def analyze_char(char):
    if not char or len(char) != 1:
        return None
    if not ('\u4e00' <= char <= '\u9fff'):
        return None
    if not HAS_VOCAB:
        return None

    try:
        result = {
            'char': char,
            'pinyin': get_pinyin(char),
        }

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
            result['components'] = [
                {
                    'zh': c.get('zh', ''),
                    'pinyin': c.get('pinyin', ''),
                    'meaning': c.get('meaning', ''),
                    'position': c.get('position', ''),
                }
                for c in comps[:8]
            ]

        mnemonic = generate_mnemonic(char)
        if mnemonic:
            result['mnemonic'] = mnemonic

        similar = find_similar_chars(char)
        if similar:
            result['similar'] = similar

        return result

    except Exception as e:
        print("[VocabAPI] analyze error '" + str(char) + "': " + str(e))
        return None


# ═══════════════════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════════════════
@app.route('/health')
def health():
    return jsonify({
        'ok': True,
        'has_vocab': HAS_VOCAB,
        'version': '1.0',
    })


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
                'ok': False,
                'error': 'Analysis failed',
                'char': char,
            }), 500

        return jsonify({
            'ok': True,
            'data': result,
        })

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

        return jsonify({
            'ok': True,
            'data': result,
        })

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/test')
def test_get():
    ch = request.args.get('char', '').strip()

    if not ch:
        return '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Test Vocab API</title>
<style>
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       max-width: 700px; margin: 40px auto; padding: 0 20px;
       background: #f9fafb; color: #111827; line-height: 1.5; }
h1 { color: #4f46e5; font-size: 1.5rem; }
input { padding: 10px 14px; font-size: 16px; border: 2px solid #ccc;
        border-radius: 8px; width: 200px; }
button { padding: 10px 20px; font-size: 16px; background: #4f46e5;
         color: #fff; border: none; border-radius: 8px; cursor: pointer; }
button:hover { background: #4338ca; }
.hint { color: #666; font-size: 14px; margin-top: 10px; }
.example { display: inline-block; margin: 4px; padding: 8px 14px;
           background: #f3f4f6; border-radius: 6px; cursor: pointer;
           font-size: 18px; font-family: "PingFang SC", sans-serif; }
.example:hover { background: #e5e7eb; }
a { color: #4f46e5; }
</style>
</head>
<body>
<h1>🔍 Chinese Vocab API Test</h1>
<p>Nhập 1 chữ Hán để phân tích bộ thủ + mẹo nhớ:</p>
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
<span class="example" onclick="go('明')">明</span>
<span class="example" onclick="go('海')">海</span>
<span class="example" onclick="go('花')">花</span>
<span class="example" onclick="go('好')">好</span>
<span class="example" onclick="go('学')">学</span>
</div>
<script>
function go(c) {
    document.querySelector('input').value = c;
    document.querySelector('form').submit();
}
</script>
<hr style="margin: 30px 0;">
<p class="hint">
Endpoints: <a href="/health">/health</a> —
<code>POST /analyze</code> — <code>POST /analyze_batch</code>
</p>
</body>
</html>'''

    if len(ch) != 1:
        return jsonify({'ok': False, 'error': 'Chỉ nhập 1 ký tự'}), 400

    result = analyze_char(ch)

    if not result:
        return '''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Lỗi</title>
<style>
body { font-family: sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; }
.err { background: #fee2e2; color: #b91c1c; padding: 20px; border-radius: 8px; }
a { color: #4f46e5; }
</style></head>
<body>
<div class="err">
<h2>❌ Không phân tích được: ''' + ch + '''</h2>
<p>Có thể do:</p>
<ul>
<li>Chữ không nằm trong database</li>
<li>Module vocab_data chưa load (check /health)</li>
</ul>
</div>
<p><a href="/test">← Thử chữ khác</a></p>
</body>
</html>''', 500

    rad = result.get('radical') or {}
    comps = result.get('components') or []
    mnemonic = result.get('mnemonic') or '(Chưa có mẹo nhớ)'
    similar = result.get('similar') or {}
    pinyin_str = result.get('pinyin') or ''

    comps_html = ''
    if comps:
        for c in comps:
            comps_html += (
                '<div class="comp-item">'
                '<span class="comp-char">' + (c.get('zh') or '') + '</span>'
                '<span class="comp-py">' + (c.get('pinyin') or '') + '</span>'
                '<span class="comp-meaning">' + (c.get('meaning') or '') + '</span>'
                '</div>'
            )
    else:
        comps_html = '<p style="color:#999;">Không có dữ liệu thành phần</p>'

    rad_html = ''
    if rad:
        rad_html = (
            '<div class="radical-box">'
            '<span class="rad-char">' + (rad.get('zh') or '') + '</span>'
            '<span class="rad-name">Bộ ' + (rad.get('pinyin') or '') + '</span>'
            '<span class="rad-meaning">' + (rad.get('meaning') or '') + '</span>'
            '</div>'
        )
    else:
        rad_html = '<p style="color:#999;">Không xác định</p>'

    similar_html = ''
    if similar:
        sim_list = similar.get('similar') or []
        diff = similar.get('diff') or ''
        if sim_list:
            sim_chars = ''.join(
                '<span class="similar-char">' + str(c) + '</span>'
                for c in sim_list
            )
            similar_html = (
                '<div class="similar-box">'
                '<div class="similar-title">🔍 Dễ nhầm</div>'
                '<div class="similar-chars">' + sim_chars + '</div>'
            )
            if diff:
                similar_html += '<div class="similar-diff">📌 ' + diff + '</div>'
            similar_html += '</div>'

    mnemonic_escaped = (mnemonic
                        .replace('&', '&amp;')
                        .replace('<', '&lt;')
                        .replace('>', '&gt;')
                        .replace('\n', '<br>'))

    html = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Phân tích: ''' + ch + '''</title>
<style>
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       max-width: 700px; margin: 30px auto; padding: 0 20px;
       background: #f9fafb; color: #111827; line-height: 1.5; }
h1 { color: #4f46e5; font-size: 1.3rem; margin-bottom: 1rem; }
.main-char { font-size: 5rem; font-weight: 700; text-align: center;
             font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
             margin: 1rem 0 .25rem; line-height: 1; color: #111827; }
.main-pinyin { text-align: center; font-size: 1.3rem; font-style: italic;
               color: #6b7280; margin-bottom: 1.5rem; }
.section { background: #fff; border-radius: 12px; padding: 1rem 1.25rem;
           margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.section-title { font-size: .8rem; font-weight: 700; text-transform: uppercase;
                 letter-spacing: .5px; color: #6b7280; margin-bottom: .75rem; }
.radical-box { display: flex; align-items: center; gap: .75rem; flex-wrap: wrap; }
.rad-char { font-size: 2.5rem; font-weight: 700;
            font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
            color: #1d4ed8; line-height: 1; }
.rad-name { font-size: 1rem; font-weight: 700; color: #1d4ed8;
            background: #dbeafe; padding: .25rem .6rem; border-radius: 6px; }
.rad-meaning { font-size: .95rem; color: #374151; }
.comp-item { display: flex; align-items: center; gap: .75rem;
             padding: .6rem .75rem; border-radius: 8px;
             background: #f9fafb; margin-bottom: .5rem; }
.comp-item:last-child { margin-bottom: 0; }
.comp-char { font-size: 1.75rem; font-weight: 700; min-width: 1.5em;
             font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
             color: #111827; line-height: 1; }
.comp-py { font-size: .85rem; font-style: italic; color: #6b7280;
           min-width: 4em; }
.comp-meaning { font-size: .9rem; color: #374151; flex: 1; }
.mnemonic-box { background: #fffbeb; border-left: 4px solid #f59e0b;
                padding: .85rem 1rem; border-radius: 8px;
                font-size: .95rem; color: #78350f; line-height: 1.7; }
.similar-box { background: #fef2f2; border-left: 4px solid #ef4444;
               padding: .75rem 1rem; border-radius: 8px; margin-top: .75rem; }
.similar-title { font-weight: 700; color: #b91c1c; font-size: .85rem;
                 margin-bottom: .5rem; }
.similar-chars { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: .5rem; }
.similar-char { font-size: 1.5rem; font-weight: 700; padding: .25rem .6rem;
                background: #fff; border-radius: 6px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
                border: 1px solid #fecaca; }
.similar-diff { font-size: .85rem; color: #7f1d1d; }
.back-btn { display: inline-block; margin-top: 1rem; padding: .6rem 1.2rem;
            background: #4f46e5; color: #fff; border-radius: 8px;
            font-weight: 600; text-decoration: none; }
.back-btn:hover { background: #4338ca; }
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
<div class="mnemonic-box">''' + mnemonic_escaped + '''</div>
''' + similar_html + '''
</div>
<a href="/test" class="back-btn">← Phân tích chữ khác</a>
</body>
</html>'''

    return html


@app.route('/')
def index():
    return jsonify({
        'name': 'Chinese Vocab Analysis API',
        'version': '1.0',
        'endpoints': {
            'health': 'GET /health',
            'test': 'GET /test?char=权',
            'analyze': 'POST /analyze  { char: "权" }',
            'analyze_batch': 'POST /analyze_batch  { chars: ["权", "管"] }',
        }
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
