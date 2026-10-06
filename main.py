# -*- coding: utf-8 -*-
"""Chinese Vocab Analysis API"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pypinyin import pinyin, Style
import os
import json
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HAS_VOCAB = False
try:
    from vocab_data.radical_analyzer import (
        _split_components, get_radical_for_word
    )
    from vocab_data.mnemonic_generator import generate_mnemonic
    HAS_VOCAB = True
    print("[VocabAPI] vocab_data loaded OK")
except Exception as e:
    print("[VocabAPI] vocab_data load failed: " + str(e))


_AI_MNEMONICS = {}
_AI_MNEMONICS_INDEX = {}
_AI_MNEMONICS_PATH = None
_AI_MNEMONICS_MTIME = 0
_AI_MNEMONICS_LOADED = False


def _find_ai_mnemonics_file():
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
    idx = {}
    for k, v in data.items():
        parts = k.split("|")
        if len(parts) != 3:
            continue
        zh = parts[2].strip()
        if not zh:
            continue
        if zh not in idx:
            idx[zh] = v
    return idx


def _do_load_ai_mnemonics():
    global _AI_MNEMONICS, _AI_MNEMONICS_INDEX
    global _AI_MNEMONICS_PATH, _AI_MNEMONICS_MTIME, _AI_MNEMONICS_LOADED

    path = _find_ai_mnemonics_file()
    if not path:
        _AI_MNEMONICS = {}
        _AI_MNEMONICS_INDEX = {}
        _AI_MNEMONICS_PATH = None
        _AI_MNEMONICS_MTIME = 0
        _AI_MNEMONICS_LOADED = True
        print("[VocabAPI] [INFO] Khong co ai_mnemonics.json")
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return False

        _AI_MNEMONICS = data
        _AI_MNEMONICS_INDEX = _build_ai_index(data)
        _AI_MNEMONICS_PATH = path
        _AI_MNEMONICS_MTIME = os.path.getmtime(path)
        _AI_MNEMONICS_LOADED = True

        print("[VocabAPI] [OK] Load " + str(len(data)) + " meo nho AI")
        print("[VocabAPI] [OK] Index: " + str(len(_AI_MNEMONICS_INDEX)) + " chu")
        return True
    except Exception as e:
        print("[VocabAPI] [WARN] Loi doc ai_mnemonics.json: " + str(e))
        return False


def load_ai_mnemonics():
    _do_load_ai_mnemonics()


def _check_ai_mnemonics_fresh():
    if not _AI_MNEMONICS_LOADED:
        _do_load_ai_mnemonics()
        return

    path = _AI_MNEMONICS_PATH

    if not path:
        new_path = _find_ai_mnemonics_file()
        if new_path:
            _do_load_ai_mnemonics()
        return

    if not os.path.exists(path):
        _do_load_ai_mnemonics()
        return

    try:
        current_mtime = os.path.getmtime(path)
        if current_mtime > _AI_MNEMONICS_MTIME:
            _do_load_ai_mnemonics()
    except Exception:
        pass


def get_ai_mnemonic(char):
    _check_ai_mnemonics_fresh()
    if not _AI_MNEMONICS_INDEX:
        return ""
    char = str(char or "").strip()
    if not char:
        return ""
    return _AI_MNEMONICS_INDEX.get(char, "")


_VOCAB_MEANINGS = {}
_VOCAB_MEANINGS_PATH = None
_VOCAB_MEANINGS_MTIME = 0


def _find_vocab_meanings_file():
    here = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(here)
    candidates = [
        os.path.join(here, "data", "vocab_meanings.json"),
        os.path.join(here, "vocab_data", "vocab_meanings.json"),
        os.path.join(parent, "data", "vocab_meanings.json"),
        "data/vocab_meanings.json",
        "vocab_data/vocab_meanings.json",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _do_load_vocab_meanings():
    global _VOCAB_MEANINGS, _VOCAB_MEANINGS_PATH, _VOCAB_MEANINGS_MTIME
    path = _find_vocab_meanings_file()
    if not path:
        _VOCAB_MEANINGS = {}
        _VOCAB_MEANINGS_PATH = None
        _VOCAB_MEANINGS_MTIME = 0
        print("[VocabAPI] [INFO] Khong co vocab_meanings.json")
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            _VOCAB_MEANINGS = data
            _VOCAB_MEANINGS_PATH = path
            _VOCAB_MEANINGS_MTIME = os.path.getmtime(path)
            print("[VocabAPI] [OK] Load " + str(len(data)) + " nghia tu")
            return True
    except Exception as e:
        print("[VocabAPI] [WARN] Loi doc vocab_meanings.json: " + str(e))
    return False


def get_meaning(char):
    if not char:
        return ""
    return _VOCAB_MEANINGS.get(char, "")


def _check_vocab_meanings_fresh():
    path = _VOCAB_MEANINGS_PATH
    if not path:
        new_path = _find_vocab_meanings_file()
        if new_path:
            _do_load_vocab_meanings()
        return
    if not os.path.exists(path):
        _do_load_vocab_meanings()
        return
    try:
        if os.path.getmtime(path) > _VOCAB_MEANINGS_MTIME:
            _do_load_vocab_meanings()
    except Exception:
        pass


_SIMILAR_CHARS = {}
_SIMILAR_CHARS_LOADED = False


def _do_load_similar_chars():
    global _SIMILAR_CHARS, _SIMILAR_CHARS_LOADED
    if _SIMILAR_CHARS_LOADED:
        return

    here = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.join(here, "vocab_data")
    if not os.path.isdir(folder):
        _SIMILAR_CHARS_LOADED = True
        return

    total = 0
    for fname in sorted(os.listdir(folder)):
        if fname.startswith("similar_chars") and fname.endswith(".json"):
            path = os.path.join(folder, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    _SIMILAR_CHARS.update(data)
                    total += len(data)
                    print("[VocabAPI] [OK] Load " + str(len(data))
                          + " similar chars tu " + fname)
            except Exception as e:
                print("[VocabAPI] [WARN] Loi doc " + fname + ": " + str(e))

    _SIMILAR_CHARS_LOADED = True
    print("[VocabAPI] [OK] Tong similar chars: " + str(total))


def get_similar_chars(char):
    if not char:
        return [], ""
    entry = _SIMILAR_CHARS.get(char)
    if not entry:
        return [], ""

    if isinstance(entry, list):
        return [str(c).strip() for c in entry if c], ""

    if isinstance(entry, dict):
        chars = entry.get('similar', []) or []
        diff = entry.get('diff', '') or ''
        return [str(c).strip() for c in chars if c], diff

    return [], ""


app = Flask(__name__)
CORS(app)

load_ai_mnemonics()
_do_load_vocab_meanings()
_do_load_similar_chars()


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
        result = {'char': char, 'pinyin': get_pinyin(char)}

        _check_vocab_meanings_fresh()
        vi = get_meaning(char)
        if vi:
            result['vi'] = vi

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

        mnemonic = get_ai_mnemonic(char)
        if not mnemonic:
            mnemonic = generate_mnemonic(char)
        if mnemonic:
            result['mnemonic'] = mnemonic

        sim_chars, diff_text = get_similar_chars(char)
        if sim_chars:
            similar_full = []
            for c in sim_chars:
                if not c or len(c) != 1:
                    continue
                c_vi = get_meaning(c)
                similar_full.append({
                    'char': c,
                    'pinyin': get_pinyin(c),
                    'meaning': c_vi,
                    'breakdown': '',
                })
            if similar_full:
                result['similar'] = {
                    'list': similar_full,
                    'diff': diff_text,
                }

        return result
    except Exception as e:
        print("[VocabAPI] analyze error '" + str(char) + "': " + str(e))
        return None


def render_test_page(ch):
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
<h1>Chinese Vocab API Test</h1>
<p>Nhap 1 chu Han de phan tich:</p>
<form method="GET" action="/test">
<input type="text" name="char" placeholder="VD: 权" maxlength="1" autofocus>
<button type="submit">Phan tich</button>
</form>
<p class="hint">Hoac bam thu:</p>
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
<p class="hint">Endpoints: <a href="/health">/health</a> - <a href="/debug?char=爱">/debug</a></p>
</body>
</html>'''

    if len(ch) != 1:
        return '<h1>Chi nhap 1 ky tu</h1><p><a href="/test">Quay lai</a></p>'

    result = analyze_char(ch)

    if not result:
        return '<h1>Khong phan tich duoc: ' + ch + '</h1><p><a href="/test">Thu chu khac</a></p>'

    rad = result.get('radical') or {}
    comps = result.get('components') or []
    mnemonic = result.get('mnemonic') or '(Chua co meo nho)'
    similar = result.get('similar') or {}
    pinyin_str = result.get('pinyin') or ''
    vi_str = result.get('vi') or ''

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
        comps_html = '<p style="color:#999">Khong co du lieu</p>'

    if rad:
        rad_html = (
            '<div class="radical-box">'
            '<span class="rad-char">' + (rad.get('zh') or '') + '</span>'
            '<span class="rad-name">Bo ' + (rad.get('pinyin') or '') + '</span>'
            '<span class="rad-meaning">' + (rad.get('meaning') or '') + '</span>'
            '</div>'
        )
    else:
        rad_html = '<p style="color:#999">Khong xac dinh</p>'

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
            '<div class="similar-title">De nham</div>'
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
<title>Phan tich: ''' + ch + '''</title>
<style>
body{font-family:-apple-system,sans-serif;max-width:700px;margin:30px auto;padding:0 20px;background:#f9fafb;color:#111827;line-height:1.5}
h1{color:#4f46e5;font-size:1.3rem}
.main-char{font-size:5rem;font-weight:700;text-align:center;font-family:"PingFang SC","Microsoft YaHei",sans-serif;margin:1rem 0 .25rem;line-height:1}
.main-pinyin{text-align:center;font-size:1.3rem;font-style:italic;color:#6b7280;margin-bottom:.25rem}
.main-vi{text-align:center;font-size:1rem;color:#374151;margin-bottom:1.5rem}
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
<h1>Ket qua phan tich</h1>
<div class="main-char">''' + ch + '''</div>
<div class="main-pinyin">''' + pinyin_str + '''</div>
<div class="main-vi">''' + vi_str + '''</div>
<div class="section">
<div class="section-title">Bo thu chinh</div>
''' + rad_html + '''
</div>
<div class="section">
<div class="section-title">Thanh phan cau tao</div>
''' + comps_html + '''
</div>
<div class="section">
<div class="section-title">Meo nho</div>
<div class="mnemonic-box">''' + mnem_esc + '''</div>
''' + similar_html + '''
</div>
<a href="/test" class="back-btn">Phan tich chu khac</a>
</body>
</html>'''


@app.route('/health')
def health():
    return jsonify({
        'ok': True,
        'has_vocab': HAS_VOCAB,
        'ai_mnemonics_loaded': len(_AI_MNEMONICS),
        'ai_index_size': len(_AI_MNEMONICS_INDEX),
        'ai_file_path': _AI_MNEMONICS_PATH,
        'ai_file_mtime': _AI_MNEMONICS_MTIME,
        'vocab_meanings_loaded': len(_VOCAB_MEANINGS),
        'vocab_meanings_path': _VOCAB_MEANINGS_PATH,
        'similar_chars_loaded': len(_SIMILAR_CHARS),
        'version': '1.6',
    })


@app.route('/reload', methods=['POST', 'GET'])
def reload_ai():
    ok = _do_load_ai_mnemonics()
    _do_load_vocab_meanings()
    return jsonify({
        'ok': ok,
        'count': len(_AI_MNEMONICS),
        'index_size': len(_AI_MNEMONICS_INDEX),
        'path': _AI_MNEMONICS_PATH,
        'mtime': _AI_MNEMONICS_MTIME,
        'meanings_count': len(_VOCAB_MEANINGS),
        'similar_count': len(_SIMILAR_CHARS),
    })


@app.route('/debug')
def debug():
    try:
        ch = request.args.get('char', '').strip()
        if not ch:
            return jsonify({'error': 'Missing ?char=...'})

        _check_vocab_meanings_fresh()

        ai_mnemonic = get_ai_mnemonic(ch) or ''
        static_mnemonic = generate_mnemonic(ch) or ''
        sim_chars, diff_text = get_similar_chars(ch)
        vi = get_meaning(ch)
        analysis = analyze_char(ch) or {}

        return jsonify({
            'char': ch,
            'has_vocab': HAS_VOCAB,
            'vi': vi,
            'ai_mnemonic': ai_mnemonic,
            'static_mnemonic': static_mnemonic,
            'mnemonic_raw': ai_mnemonic if ai_mnemonic else static_mnemonic,
            'similar_chars': sim_chars,
            'similar_diff': diff_text,
            'full_analysis': analysis,
            'ai_count': len(_AI_MNEMONICS),
            'ai_index_size': len(_AI_MNEMONICS_INDEX),
            'meanings_count': len(_VOCAB_MEANINGS),
            'similar_count': len(_SIMILAR_CHARS),
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
        'version': '1.6',
        'ai_mnemonics_loaded': len(_AI_MNEMONICS),
        'ai_index_size': len(_AI_MNEMONICS_INDEX),
        'vocab_meanings_loaded': len(_VOCAB_MEANINGS),
        'similar_chars_loaded': len(_SIMILAR_CHARS),
        'endpoints': {
            'health': 'GET /health',
            'reload': 'POST /reload',
            'test': 'GET /test?char=权',
            'debug': 'GET /debug?char=爱',
            'analyze': 'POST /analyze  { char: "权" }',
            'analyze_batch': 'POST /analyze_batch  { chars: ["权"] }',
        }
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
