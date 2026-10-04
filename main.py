# -*- coding: utf-8 -*-
"""
Chinese Vocab Analysis API
- POST /analyze       { "char": "权" }
- POST /analyze_batch { "chars": ["权", "管"] }
- GET  /test?char=权  — test bằng trình duyệt
- GET  /debug?char=爱 — debug data raw
- GET  /health
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pypinyin import pinyin, Style

import os
import re
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


# ═══════════════════════════════════════════════════════════════
#  HELPER
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
    """
    Parse chuỗi diff thành dict.
    Input:  "爱=yêu (爫+冖+友); 受=nhận (爫+冖+又); 爰=viện"
    Output: {
        "爱": {"meaning": "yêu", "breakdown": "爫+冖+友"},
        "受": {"meaning": "nhận", "breakdown": "爫+冖+又"},
        "爰": {"meaning": "viện", "breakdown": ""}
    }
    """
    result = {}
    if not diff_text:
        return result

    parts = [p.strip() for p in diff_text.split(';')]

    for p in parts:
        if '=' not in p:
            continue

        ch_part, rest = p.split('=', 1)
        ch_part = ch_part.strip()

        if len(ch_part) != 1 or not ('\u4e00' <= ch_part <= '\u9fff'):
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
    """Cắt bỏ phần '🔍 Dễ nhầm...' khỏi mnemonic."""
    if not mnemonic:
        return mnemonic

    # Các marker bắt đầu phần "Dễ nhầm"
    markers = ['\n🔍', '\n📌', '\n\n🔍', '\n\n📌', '\n\n🔍 Dễ nhầm']

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
        result = {
            'char': char,
            'pinyin': get_pinyin(char),
        }

        # ═══ Bộ thủ chính ═══
        main_rad = get_radical_for_word(char)
        if main_rad:
            result['radical'] = {
                'zh': main_rad.get('zh', ''),
                'pinyin': main_rad.get('pinyin', ''),
                'meaning': main_rad.get('meaning', ''),
                'strokes': main_rad.get('strokes', 0),
                'position': main_rad.get('position', ''),
            }

        # ═══ Thành phần ═══
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

        # ═══ Mẹo nhớ — cắt bỏ "Dễ nhầm" ═══
        mnemonic = generate_mnemonic(char)
        if mnemonic:
            mnemonic = strip_similar_from_mnemonic(mnemonic)
            result['mnemonic'] = mnemonic

        # ═══ Chữ dễ nhầm — parse pinyin + nghĩa ═══
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
#  ROUTES
# ═══════════════════════════════════════════════════════════════
@app.route('/health')
def health():
    return jsonify({
        'ok': True,
        'has_vocab': HAS_VOCAB,
        'version': '1.3',
    })


@app.route('/debug')
def debug():
    ch = request.args.get('char', '').strip()
    if not ch:
        return jsonify({'error': 'Missing ?char=...'})

    similar_raw = None
    diff_text = ''
    parsed = {}
    mnemonic_raw = ''
    mnemonic_stripped = ''
    error = None

    try:
        similar_raw = find_similar_chars(ch)
        if similar_raw:
            diff_text = similar_raw.get('diff', '')
            parsed = parse_similar_diff(diff_text)
        mnemonic_raw = generate_mnemonic(ch) or ''
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
        'mnemonic_raw': mnemonic_raw,
        'mnemonic_stripped': mnemonic_stripped,
        'pinyin_test': {
            '爱': get_pinyin('爱'),
            '受': get_pinyin('受'),
            '爰': get_pinyin('爰'),
        }
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
        chars = data.get('你chars', [])

        if not isinstance(chars, list')):
            return jsonify({'ok': False, 'error">': 'chars must be array'}), 400

你        if len(chars) > 20:
</            return jsonify({'ok': False, 'error': 'Max 20 chars'}), 400

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
<span class="example" onclick="go('span>
<span class="example" onclick="go('爱')">爱</span>
<span class="example" onclick="go('想')">想</span>
<span class="example" onclick="go('明')">明</span>
<span class="example" onclick="go('海')">海</span>
<span class="example" onclick="go('花')">花</span>
<span class="example" onclick="go('很')">很</span>
<span class="example" onclick="go('天')">天</span>
<span class="example" onclick="go('未')">未</span>
<span class="example" onclick="go('妈')">妈</span>
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
<a href="/debug?char=爱">/debug?char=爱</a> —
<code>POST /analyze</code>
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
    mnemonic = result.get('mnemonic') or '(Chưa có mẹo nhớ cho chữ này)'
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
                    '<div class="sim-py">' + (py or '') + '</div>'
                    '<div class="sim-vi">' + (vi or '') + '</div>'
                    + (('<div class="sim-bd">' + bd + '</div>') if bd else '') +
                    '</div>'
                )
            similar_html = (
                '<div class="similar-box">'
                '<div class="similar-title">🔍 Dễ nhầm</div>'
                '<div class="similar-cards">' + cards_html + '</div>'
                '</div>'
            )

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
.rad-meaning { font-size=: .95rem; color: #374151; }
500.comp-item { display: flex; align-items:0 center; gap: .75rem;
            )
 padding: .6rem .75rem; border-radius```

: 8px;
             background: #f9---

fafb; margin-bottom: .5rem; }
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
               padding: .85rem 1rem; border-radius: 8px; margin-top: .75rem; }
.similar-title { font-weight: 700; color: #b91c1c; font-size: .9rem;
                 margin-bottom: .6rem; }
.similar-cards { display: flex; gap: .6rem; flex-wrap: wrap; }
.similar-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 80px;
    padding: .65rem .75rem;
    background: #fff;
    border: 2px solid #fecaca;
    border-radius: 10px;
    transition: all .15s;
}
.similar-card:hover {
    transform: translateY(-3px);
    border-color: #ef4444;
    box-shadow: 0 4px 12px rgba(239, 68, 68, .15);
}
.sim-char {
    font-size: 2rem;
    font-weight: 700;
    font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
    color: #111827;
    line-height: 1;
    margin-bottom: .3rem;
}
.sim-py {
    font-size: .8rem;
    font-style: italic;
    color: #6b7280;
    margin-bottom: .25rem;
}
.sim-vi {
    font-size: .78rem;
    color: #b91c1c;
    font-weight: 700;
    text-align: center;
    margin-bottom: .2rem;
}
.sim-bd {
    font-size: .65rem;
    color: #9ca3af;
    text-align: center;
    font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
    line-height: 1.3;
    padding-top: .2rem;
    border-top: 1px dashed #e5e7eb;
    margin-top: .2rem;
    width: 100%;
}
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
        'version': '1.3',
        'endpoints': {
            'health': 'GET /health',
            'test': 'GET /test?char=权',
            'debug': 'GET /debug?char=爱',
            'analyze': 'POST /analyze  { char: "权" }',
            'analyze_batch': 'POST /analyze_batch  { chars: ["权", "管"] }',
        }
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port## 📋 Những gì đã thay đổi

| # | Sửa gì |
|---|--------|
| 1 | Thêm hàm `strip_similar_from_mnemonic()` — cắt "🔍 Dễ nhầm" khỏi mnemonic |
| 2 | `analyze_char()` — gọi hàm trên khi lấy mnemonic |
| 3 | Route `/test` — **luôn hiện box card** similar (bỏ điều kiện `'Dễ nhầm' not in mnemonic`) |
| 4 | Route `/debug` — thêm `mnemonic_raw` + `mnemonic_stripped` để so sánh |
| 5 | Version `1.2` → `1.3` |

---

## 🎯 Sau khi push lên GitHub

Đợi Render deploy (~2 phút), test:
