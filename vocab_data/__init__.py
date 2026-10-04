# -*- coding: utf-8 -*-
"""
Package xử lý dữ liệu từ vựng HSK.
Bao gồm:
  - radicals_db         : Database 214 bộ thủ Khang Hy
  - radical_analyzer    : Phân tích chữ Hán → tìm bộ thủ
  - mnemonic_generator  : Sinh mẹo nhớ tự động
"""

from .radicals_db import RADICALS, SIMPLIFIED_VARIANTS, get_radical_info
from .radical_analyzer import analyze_word, find_components, get_radical_for_word
from .mnemonic_generator import generate_mnemonic

__all__ = [
    "RADICALS",
    "SIMPLIFIED_VARIANTS",
    "get_radical_info",
    "analyze_word",
    "find_components",
    "get_radical_for_word",
    "generate_mnemonic",
]
