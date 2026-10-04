# -*- coding: utf-8 -*-
"""
Chinese Vocab Analysis API
- POST /analyze  { "char": "权" }
- POST /analyze_batch  { "chars": ["权", "管"] }
- GET /health
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pypinyin import pinyin, Style

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ═══ Import vocab_data ═══
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


def analyze_char(char):
    """Phân tích đầy đủ 1 ký tự."""
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

        # ═══ Mẹo nhớ ═══
        mnemonic = generate_mnemonic(char)
        if mnemonic:
            result['mnemonic'] = mnemonic

        # ═══ Chữ dễ nhầm ═══
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
    """
    Body: { "char": "权" }
    Return: { "ok": true, "data": {...} }
    """
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
    """
    Body: { "chars": ["权", "管", "你"] }
    Return: { "ok": true, "data": { "权": {...}, "管": {...} } }
    """
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


@app.route('/')
def index():
    return jsonify({
        'name': 'Chinese Vocab Analysis API',
        'version': '1.0',
        'endpoints': {
            'health': 'GET /health',
            'analyze': 'POST /analyze  { char: "权" }',
            'analyze_batch': 'POST /analyze_batch  { chars: ["权", "管"] }',
        }
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
