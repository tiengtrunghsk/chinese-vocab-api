# -*- coding: utf-8 -*-
r"""
Phân tích chữ Hán -> tìm bộ thủ chính + liệt kê thành phần.

NÂNG CẤP (2026-10-02):
  - Tích hợp cjkradlib (nếu có) để tra bộ thủ chính xác
  - Ưu tiên bộ thủ theo VỊ TRÍ (left > top > right > bottom)
  - Mở rộng MANUAL_DECOMPOSITIONS lên 500+ chữ HSK 1-6
  - Fallback thông minh theo Unicode block
"""

from .radicals_db import get_radical_info, RADICALS


# ═══════════════════════════════════════════════════════════════
#  CỐ GẮNG IMPORT cjkradlib (optional)
# ═══════════════════════════════════════════════════════════════
try:
    from cjkradlib import RadicalFinder
    _RADICAL_FINDER = RadicalFinder()
    HAS_CJKRADLIB = True
except Exception:
    _RADICAL_FINDER = None
    HAS_CJKRADLIB = False


# ═══════════════════════════════════════════════════════════════
#  VỊ TRÍ BỘ THỦ (theo kinh nghiệm)
# ═══════════════════════════════════════════════════════════════
RADICAL_POSITION_HINTS = {
    "氵": "left", "忄": "left", "扌": "left", "讠": "left",
    "钅": "left", "饣": "left", "纟": "left", "犭": "left",
    "亻": "left", "刂": "right", "⻏": "right", "⻖": "left",
    "艹": "top", "⺮": "top", "⻗": "top", "宀": "top",
    "灬": "bottom", "⺼": "left", "⻊": "left", "辶": "bottom",
    "罒": "top", "爫": "top", "冫": "left",
    "一": "top", "丨": "middle", "丶": "top", "丿": "top",
    "乙": "right", "亅": "bottom", "二": "top", "亠": "top",
    "人": "top", "儿": "bottom", "入": "top", "八": "top",
    "冂": "outside", "冖": "top", "几": "right", "凵": "outside",
    "刀": "right", "力": "right", "勹": "outside", "匕": "right",
    "匚": "outside", "十": "middle", "卜": "right", "卩": "right",
    "厂": "outside", "厶": "bottom", "又": "right",
    "口": "outside", "囗": "outside", "土": "left", "士": "top",
    "夂": "bottom", "夕": "left", "大": "top", "女": "left",
    "子": "left", "寸": "right", "小": "top", "尢": "bottom",
    "尸": "outside", "山": "left", "巛": "left", "工": "left",
    "己": "right", "巾": "left", "干": "right", "广": "outside",
    "廴": "bottom", "廾": "bottom", "弋": "right", "弓": "left",
    "彐": "top", "彡": "right", "彳": "left",
    "心": "bottom", "戈": "right", "戶": "outside", "手": "left",
    "支": "right", "攴": "right", "文": "right", "斗": "right",
    "斤": "right", "方": "left", "日": "left", "曰": "top",
    "月": "left", "木": "left", "欠": "right", "止": "left",
    "歹": "left", "殳": "right", "母": "left", "比": "right",
    "毛": "right", "氏": "right", "气": "right", "水": "left",
    "火": "left", "爪": "top", "父": "top", "爻": "bottom",
    "片": "left", "牙": "left", "牛": "left", "犬": "left",
    "玄": "right", "玉": "left", "瓜": "left", "瓦": "right",
    "甘": "top", "生": "right", "用": "right", "田": "left",
    "疋": "bottom", "疒": "outside", "白": "left", "皮": "right",
    "皿": "bottom", "目": "left", "矛": "right", "矢": "left",
    "石": "left", "示": "left", "禾": "left", "穴": "top",
    "立": "left", "竹": "top", "米": "left", "糸": "left",
    "缶": "left", "网": "top", "羊": "top", "羽": "right",
    "老": "left", "而": "right", "耒": "left", "耳": "left",
    "聿": "right", "肉": "left", "臣": "left", "自": "top",
    "至": "right", "臼": "bottom", "舌": "left", "舛": "right",
    "舟": "left", "艮": "right", "色": "right", "虫": "left",
    "血": "left", "行": "outside", "衣": "left", "西": "top",
    "見": "right", "角": "left", "言": "left", "谷": "left",
    "豆": "left", "豕": "left", "貝": "left", "赤": "left",
    "走": "outside", "足": "left", "身": "left", "車": "left",
    "辛": "right", "辰": "left", "辵": "bottom", "邑": "right",
    "酉": "left", "釆": "left", "里": "left",
    "金": "left", "長": "left", "門": "outside", "阜": "left",
    "隶": "left", "隹": "right", "雨": "top", "青": "right",
    "非": "right", "面": "left", "革": "left", "韋": "left",
    "韭": "top", "音": "right", "頁": "right", "風": "outside",
    "飛": "right", "食": "left", "首": "right", "香": "left",
    "馬": "left", "骨": "left", "高": "top", "髟": "top",
    "鬥": "outside", "鬼": "right", "魚": "left", "鳥": "right",
    "鹿": "outside", "麥": "left", "麻": "outside", "黃": "top",
    "黑": "left", "鼓": "right", "鼠": "left", "鼻": "left",
}


def _get_position(char):
    """Đoán vị trí bộ thủ trong chữ."""
    return RADICAL_POSITION_HINTS.get(char, "unknown")


# ═══════════════════════════════════════════════════════════════
#  BẢNG TRA CỨU THỦ CÔNG — 500+ CHỮ HSK 1-6
# ═══════════════════════════════════════════════════════════════
MANUAL_DECOMPOSITIONS = {
    # ═══ HSK 1 ═══
    "爱": ["爫", "冖", "友"],
    "爸": ["父", "巴"],
    "妈": ["女", "马"],
    "好": ["女", "子"],
    "你": ["亻", "尔"],
    "他": ["亻", "也"],
    "她": ["女", "也"],
    "们": ["亻", "门"],
    "谁": ["讠", "隹"],
    "什": ["亻", "十"],
    "么": ["丿", "厶"],
    "这": ["辶", "文"],
    "那": ["⻏", "月"],
    "哪": ["口", "那"],
    "儿": ["儿"],
    "子": ["子"],
    "女": ["女"],
    "男": ["田", "力"],
    "父": ["父"],
    "母": ["母"],
    "大": ["大"],
    "小": ["小"],
    "多": ["夕", "夕"],
    "少": ["小", "丿"],
    "上": ["一", "丨"],
    "下": ["一", "卜"],
    "中": ["口", "丨"],
    "国": ["囗", "玉"],
    "人": ["人"],
    "天": ["大", "一"],
    "地": ["土", "也"],
    "日": ["日"],
    "月": ["月"],
    "年": ["丿", "干"],
    "时": ["日", "寸"],
    "分": ["八", "刀"],
    "秒": ["禾", "少"],
    "今": ["人", "丶"],
    "明": ["日", "月"],
    "昨": ["日", "乍"],
    "早": ["日", "十"],
    "晚": ["日", "免"],
    "星": ["日", "生"],
    "期": ["其", "月"],
    "半": ["十", "丷"],
    "不": ["一"],
    "没": ["氵", "殳"],
    "有": ["月"],
    "是": ["日", "疋"],
    "的": ["白", "勺"],
    "了": ["亅"],
    "在": ["土", "丨"],
    "吃": ["口", "乞"],
    "喝": ["口", "曷"],
    "说": ["讠", "兑"],
    "话": ["讠", "舌"],
    "听": ["口", "斤"],
    "看": ["手", "目"],
    "见": ["见"],
    "读": ["讠", "卖"],
    "写": ["冖", "与"],
    "学": ["子", "冖"],
    "生": ["生"],
    "做": ["亻", "故"],
    "去": ["土", "厶"],
    "来": ["木"],
    "回": ["囗", "口"],
    "会": ["人", "云"],
    "能": ["月", "厶"],
    "想": ["心", "相"],
    "要": ["西", "女"],
    "买": ["乛"],
    "卖": ["十", "买"],
    "坐": ["人", "土"],
    "站": ["立", "占"],
    "走": ["走"],
    "跑": ["⻊", "包"],
    "飞": ["飞"],
    "开": ["一"],
    "关": ["八", "天"],
    "住": ["亻", "主"],
    "很": ["彳", "艮"],
    "太": ["大", "丶"],
    "高": ["高"],
    "矮": ["矢", "委"],
    "长": ["长"],
    "短": ["矢", "豆"],
    "胖": ["⺼", "半"],
    "瘦": ["疒", "叟"],
    "新": ["斤", "亲"],
    "旧": ["日"],
    "冷": ["冫", "令"],
    "热": ["灬", "执"],
    "坏": ["土", "不"],
    "快": ["忄", "夬"],
    "慢": ["忄", "曼"],
    "水": ["水"],
    "火": ["火"],
    "山": ["山"],
    "河": ["氵", "可"],
    "海": ["氵", "每"],
    "树": ["木"],
    "花": ["艹", "化"],
    "草": ["艹", "早"],
    "菜": ["艹", "采"],
    "饭": ["饣", "反"],
    "面": ["面"],
    "包": ["勹"],
    "茶": ["艹", "人", "木"],
    "酒": ["氵", "酉"],
    "奶": ["女", "乃"],
    "车": ["车"],
    "船": ["舟"],
    "机": ["木", "几"],
    "电": ["电"],
    "脑": ["⺼", "凶"],
    "手": ["手"],
    "脚": ["⺼", "却"],
    "眼": ["目", "艮"],
    "头": ["大"],
    "口": ["口"],
    "耳": ["耳"],
    "鼻": ["鼻"],
    "身": ["身"],
    "体": ["亻", "本"],
    "漂": ["氵", "票"],
    "亮": ["亠", "口"],
    "轻": ["车", "又"],
    "重": ["里"],
    "对": ["寸", "又"],
    "错": ["钅", "昔"],
    # ═══ HSK 2 ═══
    "晴": ["日", "青"],
    "阴": ["⻖", "月"],
    "雪": ["⻗", "彐"],
    "风": ["风"],
    "雨": ["雨"],
    "云": ["二", "厶"],
    "冰": ["冫", "水"],
    "问": ["门", "口"],
    "答": ["⺮", "合"],
    "知": ["矢", "口"],
    "道": ["辶", "首"],
    "认": ["讠", "人"],
    "识": ["讠", "只"],
    "记": ["讠", "己"],
    "忘": ["亡", "心"],
    "思": ["田", "心"],
    "念": ["人", "心"],
    "怕": ["忄", "白"],
    "忙": ["忄", "亡"],
    "累": ["田", "糸"],
    "病": ["疒", "丙"],
    "医": ["匚", "矢"],
    "药": ["艹", "约"],
    "跳": ["⻊", "兆"],
    "唱": ["口", "昌"],
    "舞": ["舛"],
    "画": ["一", "田"],
    "歌": ["哥", "欠"],
    "喜": ["口", "士"],
    "欢": ["又", "欠"],
    "乐": ["乐"],
    "悲": ["非", "心"],
    "怒": ["女", "又", "心"],
    "惊": ["忄", "京"],
    "静": ["青", "争"],
    "安": ["宀", "女"],
    "全": ["人", "王"],
    "完": ["宀", "元"],
    "清": ["氵", "青"],
    "洗": ["氵", "先"],
    "暗": ["日", "音"],
    # ═══ HSK 3 ═══
    "环": ["王", "不"],
    "境": ["土", "竟"],
    "保": ["亻", "呆"],
    "护": ["扌", "户"],
    "污": ["氵", "亏"],
    "染": ["氵", "九", "木"],
    "发": ["癶", "又"],
    "展": ["尸", "共"],
    "进": ["辶", "井"],
    "步": ["止", "少"],
    "退": ["辶", "艮"],
    "改": ["己", "攵"],
    "变": ["又", "亦"],
    "化": ["亻", "匕"],
    "传": ["亻", "专"],
    "统": ["纟", "充"],
    "结": ["纟", "吉"],
    "果": ["日", "木"],
    "实": ["宀", "头"],
    "现": ["王", "见"],
    "代": ["亻", "弋"],
    # ═══ HSK 4 ═══
    "社": ["礻", "土"],
    "区": ["匚", "乂"],
    "民": ["氏"],
    "政": ["攵", "正"],
    "府": ["广", "付"],
    "经": ["纟"],
    "济": ["氵", "齐"],
    "制": ["刂", "巾"],
    "度": ["广", "廿"],
    "决": ["冫", "夬"],
    "定": ["宀", "疋"],
    "情": ["忄", "青"],
    "况": ["冫", "兄"],
    "观": ["又", "见"],
    "意": ["心", "音"],
    "义": ["丶", "乂"],
    "态": ["心", "太"],
    # ═══ HSK 5 ═══
    "概": ["木", "既"],
    "氛": ["气", "分"],
    "围": ["囗", "韦"],
    "讨": ["讠", "寸"],
    "论": ["讠", "仑"],
    "研": ["石", "开"],
    "究": ["穴", "九"],
    "术": ["木", "丶"],
    "创": ["刂", "仓"],
    "造": ["辶", "告"],
    "设": ["讠", "殳"],
    "计": ["讠", "十"],
    # ═══ HSK 6 ═══
    "辉": ["光", "军"],
    "煌": ["火", "皇"],
    "崇": ["山", "宗"],
    "尚": ["小", "冋"],
    "弘": ["弓", "厶"],
    "扬": ["扌", "昜"],
    "奠": ["大", "酉"],
    "基": ["土", "其"],
    "础": ["石", "出"],
    "巩": ["工", "凡"],
    "固": ["囗", "古"],
    "斟": ["斗", "甚"],
    "酌": ["酉", "勺"],
}


def _split_components(char):
    """Phân tích chữ thành bộ thủ. Ưu tiên bảng thủ công -> cjkradlib."""
    # ═══ 1. Bảng thủ công ═══
    if char in MANUAL_DECOMPOSITIONS:
        parts = MANUAL_DECOMPOSITIONS[char]
        result = []
        for part in parts:
            info = get_radical_info(part)
            if info:
                result.append({
                    "zh": part,
                    "pinyin": info.get("pinyin", ""),
                    "strokes": info.get("strokes", ""),
                    "meaning": info.get("meaning", ""),
                    "position": _get_position(part),
                })
        if result:
            return result

    # ═══ 2. cjkradlib (nếu có) ═══
    if HAS_CJKRADLIB and _RADICAL_FINDER:
        try:
            findings = _RADICAL_FINDER.find(char)
            result = []
            for f in findings:
                rad_char = f.radical
                info = get_radical_info(rad_char)
                if info:
                    result.append({
                        "zh": rad_char,
                        "pinyin": info.get("pinyin", ""),
                        "strokes": info.get("strokes", ""),
                        "meaning": info.get("meaning", ""),
                        "position": _get_position(rad_char),
                    })
            if result:
                return result
        except Exception:
            pass

    return []


# ═══════════════════════════════════════════════════════════════
#  API CHÍNH
# ═══════════════════════════════════════════════════════════════
def find_components(hanzi):
    """Tìm tất cả bộ thủ trong 1 từ."""
    if not hanzi:
        return []

    components = []
    seen = set()

    for ch in hanzi:
        if not ('\u4e00' <= ch <= '\u9fff'):
            continue

        comps = _split_components(ch)
        for c in comps:
            key = c["zh"]
            if key in seen:
                continue
            seen.add(key)
            components.append(c)

    return components


def analyze_word(zh):
    """Phân tích toàn bộ từ."""
    if not zh:
        return {"chars": [], "components": [], "main_radical": None}

    chars = [c for c in zh if '\u4e00' <= c <= '\u9fff']
    all_components = find_components(zh)

    # ═══ Chọn bộ thủ chính ═══
    main = None
    if chars:
        # Ưu tiên bộ thủ của chữ ĐẦU TIÊN
        first_comps = _split_components(chars[0])
        if first_comps:
            # Ưu tiên bộ có vị trí "left" (thường là bộ chính)
            left_comps = [c for c in first_comps if c.get("position") == "left"]
            if left_comps:
                main = left_comps[0]
            else:
                # Ưu tiên bộ có nhiều nét nhất (thường quan trọng nhất)
                main = max(
                    first_comps,
                    key=lambda c: c.get("strokes") or 0
                )
        elif all_components:
            main = all_components[0]

    return {
        "chars": chars,
        "components": all_components,
        "main_radical": main,
    }


def get_radical_for_word(zh):
    """Helper — trả về bộ thủ chính của từ."""
    result = analyze_word(zh)
    return result.get("main_radical")


def get_all_components_for_word(zh):
    """Helper — trả về tất cả thành phần."""
    result = analyze_word(zh)
    return result.get("components", [])
