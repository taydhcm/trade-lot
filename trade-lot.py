import time
import streamlit as st
import pandas as pd
import numpy as np
import pandas_ta as ta
from vnstock import Vnstock, register_user
from datetime import datetime, timedelta
import warnings
import calendar

def scan_xanh_hong_score(df: pd.DataFrame, regime: str = "SIDEWAY") -> dict:
    """
    Hàm chấm điểm theo logic Xanh Hồng (tối đa 6 điểm)
    Trả về: score và chi tiết từng tiêu chí
    """
    try:
        if df is None or df.empty or len(df) < 30:
            return {"score": 0, "details": "Dữ liệu không đủ"}

        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        score = 0
        details = {}

        # ================== 1. TREND ==================
        ma20 = close.rolling(20).mean().iloc[-1]
        if close.iloc[-1] > ma20:
            score += 1
            details["trend"] = "✅ Trên MA20 (+1)"
        else:
            details["trend"] = "❌ Dưới MA20 (0)"

        # ================== 2. MOMENTUM (RSI) ==================
        rsi = ta.rsi(close, length=14).iloc[-1]
        if 45 < rsi < 60:
            score += 1
            details["rsi"] = f"✅ RSI đẹp ({rsi:.1f}) (+1)"
        else:
            details["rsi"] = f"❌ RSI {rsi:.1f} (0)"

        # ================== 3. FLOW (CMF) ==================
        mfm = ((close - low) - (high - close)) / (high - low)
        mfm = mfm.replace([np.inf, -np.inf], 0).fillna(0)
        cmf = (mfm * volume).rolling(21).sum() / volume.rolling(21).sum()
        cmf_value = cmf.iloc[-1]
        
        if cmf_value > -0.05:
            score += 1
            details["cmf"] = f"✅ CMF OK ({cmf_value:.3f}) (+1)"
        else:
            details["cmf"] = f"❌ CMF yếu ({cmf_value:.3f}) (0)"

        # ================== 4. TÍCH LŨY (Volatility) ==================
        range_ratio = (
            high.rolling(20).max().iloc[-1] - 
            low.rolling(20).min().iloc[-1]
        ) / close.iloc[-1]
        
        if range_ratio < 0.18:
            score += 1
            details["volatility"] = f"✅ Tích lũy tốt ({range_ratio:.1%}) (+1)"
        else:
            details["volatility"] = f"❌ Biến động lớn ({range_ratio:.1%}) (0)"

        # ================== 5. GẦN BREAKOUT ==================
        dist_to_high = (
            high.rolling(20).max().iloc[-1] - close.iloc[-1]
        ) / close.iloc[-1]
        
        if dist_to_high < 0.05:
            score += 1
            details["breakout"] = f"✅ Gần breakout ({dist_to_high:.1%}) (+1)"
        else:
            details["breakout"] = f"❌ Còn xa vùng đỉnh ({dist_to_high:.1%}) (0)"

        # ================== 6. MOMENTUM T+2 ==================
        if len(close) >= 3 and close.iloc[-1] > close.iloc[-3]:
            score += 1
            details["t2_momentum"] = "✅ Momentum T+2 (+1)"
        else:
            details["t2_momentum"] = "❌ Không có momentum ngắn hạn (0)"

        # ================== ADAPTIVE THRESHOLD ==================
        threshold = 4
        if regime == "BEAR":
            threshold = 5
        elif regime == "STRONG_BULL":
            threshold = 3.5

        passed = score >= threshold

        return {
            "score": round(score, 1),
            "max_score": 6,
            "passed": passed,
            "threshold": threshold,
            "regime": regime,
            "details": details,
            "rsi": round(rsi, 2),
            "cmf": round(cmf_value, 3),
            "range_ratio": round(range_ratio, 3)
        }

    except Exception as e:
        print(f"Lỗi scan_xanh_hong_score: {e}")
        return {"score": 0, "max_score": 6, "passed": False, "details": f"Lỗi: {e}"}

warnings.filterwarnings('ignore')

# ====================== VNSTOCK API KEY ======================
VNSTOCK_API_KEY = "vnstock_9008899a9dce77c13e296b6442ee866c"
try:
    register_user(api_key=VNSTOCK_API_KEY)
    st.success("✅ Đã đăng ký vnstock API key", icon="🔑")
except Exception as e:
    st.warning(f"⚠️ Không đăng ký được key: {e}")

st.set_page_config(page_title="Multi-View Trade Analyzer", layout="wide")
st.title("📊 Multi-View Trade - Phân tích cổ phiếu ngắn hạn")
st.markdown("**Kế hoạch trade 5-7 ngày | Target +4% | Stop -3% | Ngân sách 30 triệu**")

# ====================== DICTIONARY NGÀNH NGHỀ (copy lại từ file cũ của bạn) ======================
SECTOR_MAP = {
    "ACB": "Ngân hàng", "BID": "Ngân hàng", "VCB": "Ngân hàng", "CTG": "Ngân hàng",
    "HDB": "Ngân hàng", "MBB": "Ngân hàng", "SHB": "Ngân hàng", "STB": "Ngân hàng",
    "TCB": "Ngân hàng", "TPB": "Ngân hàng", "VPB": "Ngân hàng", "LPB": "Ngân hàng",
    "OCB": "Ngân hàng", "VIB": "Ngân hàng",
    "HPG": "Thép - Vật liệu xây dựng", "HSG": "Thép", "NKG": "Thép",
    "VHM": "Bất động sản", "VIC": "Bất động sản", "NVL": "Bất động sản",
    "PDR": "Bất động sản", "KBC": "Bất động sản", "DIG": "Bất động sản",
    "VRE": "Bất động sản", "DXG": "Bất động sản",
    "FPT": "Công nghệ - Thông tin", "MWG": "Bán lẻ", "PNJ": "Bán lẻ",
    "FRT": "Bán lẻ", "DGW": "Bán lẻ",
    "MSN": "Thực phẩm - Đồ uống", "VNM": "Sữa - Thực phẩm", "SAB": "Đồ uống",
    "QNS": "Đường", "SBT": "Đường", "LSS": "Đường",
    "POW": "Điện lực", "GAS": "Khí đốt", "PLX": "Xăng dầu",
    "VJC": "Hàng không", "TCH": "Ô tô - Linh kiện",
    "SSI": "Chứng khoán", "VCI": "Chứng khoán",
    "GEX": "Vật liệu xây dựng", "DGC": "Hóa chất", "DPM": "Phân bón",
    "DCM": "Phân bón", "BFC": "Phân bón",
    "ANV": "Thủy sản", "VHC": "Thủy sản",
    "REE": "Điện lạnh - Cơ điện", "GEG": "Điện", "PC1": "Xây dựng",
    "KDH": "Bất động sản", "NLG": "Bất động sản", "TTA": "Bất động sản",
    "HDG": "Bất động sản", "BCG": "Bất động sản",
    "SAM": "Dệt may", "TNG": "Dệt may", "VGT": "Dệt may",
    "PET": "Nhựa - Hóa chất", "CSV": "Nhựa", "LAS": "Nhựa",
    "PVS": "Dầu khí", "PVD": "Dầu khí", "PVT": "Vận tải biển",
    "HAH": "Vận tải", "VOS": "Vận tải",
    "SCS": "Logistics", "VSC": "Vận tải",
    "EIB": "Ngân hàng",
    "HHV": "Xây dựng - Hạ tầng",
    "CII": "Xây dựng - Hạ tầng",
    "MIG": "Bảo hiểm",
    "VCG": "Xây dựng - Hạ tầng",
    "GVR": "Cao su",
    "SKG": "Bất động sản",
    "VIX": "Chứng khoán",
    "GIL": "Dệt may",
    "BAB": "Ngân hàng",
    "DBC": "Nông nghiệp - Thực phẩm",
    "SZC": "Bất động sản - Khu công nghiệp",
    "MSB": "Ngân hàng",
    "VPI": "Bất động sản",
    "BVH": "Bảo hiểm",
    "IDC": "Xây dựng - Hạ tầng",
    "VND": "Chứng khoán",
    "CTS": "Chứng khoán",
    "BSI": "Chứng khoán",
    "FTS": "Chứng khoán",
    "PHR": "Cao su",
    "LCG": "Xây dựng - Hạ tầng",
    "AAA": "Nhựa - Hóa chất",
    "BSR": "Dầu khí",
}



def get_market_data(symbols):
    data = []

    for s in symbols:
        try:
            df = Vnstock().stock(symbol=s).quote.history(
                start=(datetime.now() - timedelta(days=70)).strftime("%Y-%m-%d"),
                end=datetime.now().strftime("%Y-%m-%d"),
                interval="1D"
            )
            if len(df) > 30:
                data.append(df)
        except:
            continue

        time.sleep(0.3)

    return data

def calculate_market_breadth(stock_data):
    strong = 0
    total = 0

    for df in stock_data:
        try:
            ma20 = df['close'].rolling(20).mean().iloc[-1]
            price = df['close'].iloc[-1]

            rsi = ta.rsi(df['close'], length=14).iloc[-1]

            if price > ma20 and rsi > 50:
                strong += 1

            total += 1

        except:
            continue

    if total == 0:
        return 0.5

    return strong / total

def get_vnindex_momentum():
    try:
        df_vni = Vnstock().stock(symbol="VNINDEX").quote.history(
            start=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
            end=datetime.now().strftime("%Y-%m-%d"),
            interval="1D"
        )

        rsi = ta.rsi(df_vni['close'], length=14).iloc[-1]
        change = (df_vni['close'].iloc[-1] - df_vni['close'].iloc[-2]) / df_vni['close'].iloc[-2]

        return rsi, change

    except:
        return 50, 0

def detect_market_regime(stock_data):
    breadth = calculate_market_breadth(stock_data)
    rsi, change = get_vnindex_momentum()

    # ===== FAKE BULL DETECTION =====
    if change > 0.01 and breadth < 0.45:
        return "FAKE_BULL", -1.5

    # ===== MAIN REGIME =====
    if breadth > 0.6 and rsi > 55:
        return "STRONG_BULL", +1.0

    elif breadth > 0.5:
        return "BULL", +0.5

    elif breadth < 0.4 and rsi < 45:
        return "BEAR", -1.5

    else:
        return "SIDEWAY", 0.0

def smooth_regime(regime_history):
    if len(regime_history) < 3:
        return regime_history[-1]

    last3 = regime_history[-3:]

    return max(set(last3), key=last3.count)



def get_sector(symbol):
    return SECTOR_MAP.get(symbol, "Khác / Chưa phân loại")

# ====================== TRỌNG SỐ ======================
# WEIGHTS = {
#     'Momentum': 0.28, 'Trend': 0.20, 'Volume': 0.18,
#     'Oscillator': 0.14, 'Volatility': 0.07, 'PriceAction': 0.06,
#     'Ichimoku': 0.07
# }
WEIGHTS = {
    'XH': 0.18,              # ✅ NEW (rất quan trọng)
    'Momentum': 0.20,        # giảm xuống
    'Trend': 0.18,
    'Volume': 0.14,
    'Oscillator': 0.10,
    'Volatility': 0.06,
    'PriceAction': 0.06,
    'Ichimoku': 0.08
}

def calculate_weighted_score_v2(scores_dict: dict, xh_score) -> dict:
    """
    Tính điểm tổng hợp có trọng số, xử lý an toàn None và NaN.
    Trả về dict chi tiết để debug dễ dàng.
    """
    # ====================== XỬ LÝ DỮ LIỆU ĐẦU VÀO ======================
    # Chuyển None / NaN thành giá trị mặc định
    cleaned_scores = {}
    for view, score in scores_dict.items():
        if isinstance(score, (int, float)) and pd.notna(score):  # pd.notna để kiểm tra NaN
            cleaned_scores[view] = float(score)
        else:
            cleaned_scores[view] = 5.0   # Giá trị trung lập nếu lỗi/missing

    # Xử lý xh_score
    if isinstance(xh_score, dict):
        xh_raw = xh_score.get('score', 0)
    else:
        xh_raw = xh_score if isinstance(xh_score, (int, float)) else 0

    xh_scaled = (xh_raw / 6) * 10 if xh_raw is not None else 5.0

    # Thêm XH vào dict
    cleaned_scores['XH'] = xh_scaled

    # ====================== TÍNH ĐIỂM CÓ TRỌNG SỐ ======================
    weighted = 0.0
    for view, weight in WEIGHTS.items():
        score = cleaned_scores.get(view, 5.0)
        weighted += score * weight

    # ====================== BONUS & PENALTY ======================
    # Bonus: Số view mạnh
    strong_count = sum(1 for v in cleaned_scores.values() if v >= 7.5)
    if strong_count >= 5:
        weighted += 1.5
    elif strong_count >= 4:
        weighted += 0.9
    elif strong_count >= 3:
        weighted += 0.4

    # Bonus Xanh Hồng
    if xh_raw >= 5.0:
        weighted += 1.0      # Setup rất đẹp
    elif xh_raw >= 4.0:
        weighted += 0.5

    # Penalty: Số view yếu
    weak_count = sum(1 for v in cleaned_scores.values() if v <= 4.0)
    if weak_count >= 3:
        weighted -= 1.0
    elif weak_count >= 2:
        weighted -= 0.5

    # Giới hạn điểm trong khoảng 0 - 10
    final_score = round(max(0, min(10, weighted)), 2)

    return {
        "final_score": final_score,
        "xh_scaled": round(xh_scaled, 2),
        "strong_views": strong_count,
        "weak_views": weak_count,
        "raw_scores": cleaned_scores,
        "status": "STRONG" if final_score >= 7.5 else 
                   "GOOD" if final_score >= 6.0 else 
                   "WATCH" if final_score >= 5.0 else "WEAK"
    }



# ====================== HÀM CHẤM ĐIỂM ======================
def score_momentum(crsi):
    if crsi > 68: return 9.5
    elif crsi > 58: return 8.2
    elif crsi > 52: return 7.0
    elif crsi < 45: return 3.8
    else: return 5.5

def score_trend(price, ma20, ma50):
    if price > ma20 > ma50: return 9.2
    elif ma20 > ma50: return 7.0
    elif price > ma20: return 5.5
    else: return 3.5

def score_oscillator(rsi, stoch):
    if 48 <= rsi <= 68 and stoch > 55: return 9.0
    elif 40 <= rsi <= 72: return 7.0
    elif rsi > 72 or rsi < 35: return 4.0
    else: return 5.5

def score_volume(obv_trend, vol_ratio):
    if obv_trend == "up" and vol_ratio > 1.5: return 9.5
    elif obv_trend == "up" and vol_ratio > 1.25: return 8.0
    elif obv_trend == "up": return 6.8
    elif obv_trend == "flat" and vol_ratio > 1.2: return 6.0
    elif obv_trend == "down": return 3.8
    elif vol_ratio < 0.85: return 4.0
    else: return 5.5

def score_volatility(band_width):
    if band_width < 0.08: return 8.5
    elif band_width > 0.18: return 4.5
    else: return 6.5

def score_price_action(current_price, support, df):
    if len(df) < 5: return 5.0
    distance = (current_price - support) / support
    if distance > 0.018 and df['low'].iloc[-1] <= support * 1.008:
        return 9.2
    elif 0.005 < distance <= 0.018:
        return 7.8
    elif distance <= 0.005:
        return 3.8 if df['close'].iloc[-1] < df['open'].iloc[-1] else 6.0
    else:
        return 4.5

def score_ichimoku(price, cloud_top, cloud_bottom, chikou, rsi):
    if price > cloud_top and chikou > price and rsi < 72:
        return 9.3
    elif price > cloud_top:
        return 7.8
    elif price < cloud_bottom and chikou < price:
        return 3.5
    else:
        return 5.2 if 45 <= rsi <= 65 else 4.0

# ====================== CALCULATE VIEW SCORES (ĐÃ SỬA LỖI) ======================
def calculate_view_scores(df, current_price, support, symbol):
    scores = {}
    try:
        # Basic indicators
        ma20 = df['close'].rolling(20).mean()
        ma50 = df['close'].rolling(50).mean()
        rsi = ta.rsi(df['close'], length=14).iloc[-1] if len(df) > 14 else 50.0
        stoch = ta.stoch(df['high'], df['low'], df['close'])
        stoch_k = stoch['STOCHk_14_3_3'].iloc[-1] if not stoch.empty and 'STOCHk_14_3_3' in stoch.columns else 50.0

        obv = ta.obv(df['close'], df['volume'])
        obv_trend = "up" if obv.diff().iloc[-1] > 0 else "down" if obv.diff().iloc[-1] < 0 else "flat"
        vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1] if len(df) > 20 else 1.0

        crsi = ta.crsi(df['close'], df['high'], df['low'], length=3, fast=2, slow=100).iloc[-1] if len(df) > 100 else 50.0

        # Bollinger Bands - xử lý an toàn
        bb = ta.bbands(df['close'], length=20, std=2)
        if not bb.empty and 'BBU_20_2.0' in bb.columns and 'BBL_20_2.0' in bb.columns:
            band_width = (bb['BBU_20_2.0'].iloc[-1] - bb['BBL_20_2.0'].iloc[-1]) / current_price
        else:
            band_width = 0.12

        # Ichimoku - xử lý an toàn
        ichi = ta.ichimoku(df['high'], df['low'], df['close'])
        if isinstance(ichi, tuple) and len(ichi) >= 2:
            cloud_df = ichi[0]
            cloud_top = cloud_df['ISA_9'].iloc[-1] if 'ISA_9' in cloud_df.columns else current_price
            cloud_bottom = cloud_df['ISB_26'].iloc[-1] if 'ISB_26' in cloud_df.columns else current_price
            chikou = ichi[1]['chikou'].iloc[-1] if len(ichi) > 1 and 'chikou' in ichi[1].columns else current_price
        else:
            cloud_top = cloud_bottom = chikou = current_price

    except Exception as e:
        st.warning(f"Lỗi tính indicator cho {symbol}: {str(e)[:100]}")
        rsi = stoch_k = crsi = 50.0
        obv_trend = "flat"
        vol_ratio = 1.0
        band_width = 0.12
        cloud_top = cloud_bottom = chikou = current_price

    scores['Momentum']   = score_momentum(crsi)
    scores['Trend']      = score_trend(current_price, ma20.iloc[-1] if len(ma20) > 0 else current_price, 
                                       ma50.iloc[-1] if len(ma50) > 0 else current_price)
    scores['Oscillator'] = score_oscillator(rsi, stoch_k)
    scores['Volume']     = score_volume(obv_trend, vol_ratio)
    scores['Volatility'] = score_volatility(band_width)
    scores['PriceAction']= score_price_action(current_price, support, df)
    scores['Ichimoku']   = score_ichimoku(current_price, cloud_top, cloud_bottom, chikou, rsi)

    return scores

# ====================== WEIGHTED SCORE ======================
def calculate_weighted_score(scores_dict):
    weighted = sum(scores_dict.get(view, 5.0) * weight for view, weight in WEIGHTS.items())
    strong = sum(1 for v in scores_dict.values() if v >= 7.5)
    if strong >= 5: weighted += 1.2
    elif strong >= 4: weighted += 0.8
    if scores_dict.get('Momentum', 0) >= 8.0 and scores_dict.get('Ichimoku', 0) >= 8.0:
        weighted += 1.0
    weak = sum(1 for v in scores_dict.values() if v <= 4.0)
    if weak >= 3: weighted -= 0.8
    return round(min(max(weighted, 3.0), 10.5), 2)

# ====================== FIBONACCI & MARKET CONTEXT ======================
def calculate_fibonacci(df):
    high = df['high'].rolling(60, min_periods=20).max().iloc[-1]
    low = df['low'].rolling(60, min_periods=20).min().iloc[-1]
    diff = high - low
    return round(high - diff * 0.382, 2), round(high - diff * 0.5, 2), round(high - diff * 0.618, 2)

def get_market_context():
    today = datetime.now().date()
    weekday = today.weekday()
    day_factor = 0.0
    if weekday == 0: day_factor = -0.8
    elif weekday in [2, 3]: day_factor = 0.6
    elif weekday == 4: day_factor = 0.4

    is_near_exp = False
    days_to_exp = 0
    exp_text = "—"
    year, month = today.year, today.month
    last_day = calendar.monthrange(year, month)[1]
    for d in range(max(1, last_day - 9), last_day + 1):
        try:
            check_date = datetime(year, month, d).date()
            if check_date.weekday() in [2, 3]:
                days_diff = (check_date - today).days
                if -3 <= days_diff <= 3:
                    is_near_exp = True
                    days_to_exp = days_diff
                    if days_diff == 0:
                        exp_text = "Hôm nay đáo hạn"
                    elif days_diff > 0:
                        exp_text = f"Còn {days_diff} ngày"
                    else:
                        exp_text = f"Đã qua {-days_diff} ngày"
                    break
        except:
            continue
    return day_factor, is_near_exp, days_to_exp, exp_text

def get_recommendation(final_score: float, regime: str) -> str:
    """
    Trả về khuyến nghị mua/bán dựa trên final_score và regime thị trường.
    """
    if not isinstance(final_score, (int, float)) or final_score < 0:
        return "LỖI DỮ LIỆU"

    # ===== HARD FILTER - Ưu tiên cao nhất =====
    if regime == "BEAR":
        return "KHÔNG MUA"
    
    if regime == "FAKE_BULL":
        if final_score >= 8.5:
            return "TRÁNH (BẪY TRỤ)"
        else:
            return "KHÔNG MUA"

    # ===== NORMAL REGIME =====
    if regime == "STRONG_BULL":
        if final_score >= 8.5:
            return "MUA MẠNH"
        elif final_score >= 7.2:
            return "MUA"
        elif final_score >= 6.5:
            return "THEO DÕI"
        else:
            return "LOẠI"

    elif regime == "BULL":
        if final_score >= 8.5:
            return "MUA MẠNH"
        elif final_score >= 7.4:      # bạn đã nâng threshold
            return "MUA"
        elif final_score >= 6.7:
            return "THEO DÕI"
        else:
            return "LOẠI"

    elif regime == "SIDEWAY":
        if final_score >= 8.8:        # threshold rất cao
            return "MUA NHẸ"
        elif final_score >= 7.5:
            return "THEO DÕI"
        else:
            return "LOẠI"

    # Trường hợp regime không xác định
    else:
        # Fallback logic (có thể điều chỉnh)
        if final_score >= 8.0:
            return "MUA"
        elif final_score >= 6.5:
            return "THEO DÕI"
        else:
            return "LOẠI"
# ====================== GIAO DIỆN & LOGIC CHẠY ======================
st.sidebar.header("⚙️ Cài đặt phân tích")
manual_stocks = ["HPG", "BSR", "FPT", "TCB", "SSI", "STB", "VND", "MWG", "MBB", "VHM", "VIC", "VPB", "DIG", "NVL", "GEX", "VCI", "MSN", "VNM", "ACB", "CTG", "SHB", "HDB", "VIX", "KBC", "PDR", "DXG", "VCB", "DGC", "TPB", "HSG", "NKG", "VRE", "EIB", "POW", "GAS", "LPB", "TCH", "VJC", "BID", "PLX", "SAB", "BVH", "REE", "PNJ", "GVR", "FRT", "FTS", "CTS", "BSI", "VHC", "ANV", "IDC", "KDH", "NLG", "DBC", "PVS", "PVD", "SCS", "VOS", "PVT", "HAH", "DCM", "DPM", "PC1", "GEG", "VGT", "TNG", "MSB", "OCB", "VIB", "BAB", "TTA", "BCG", "HDG", "SAM", "AAA", "PHR", "SZC", "VPI", "CII", "HHV", "LCG", "VCG", "LSS", "SBT", "QNS", "MIG", "GIL", "VNA", "SKG", "VSC"]

selection_mode = st.sidebar.radio(
    "Chế độ chọn cổ phiếu",
    options=["Chọn thủ công", "Chọn 30 cổ phiếu VN30", "Chọn 100 cổ phiếu thanh khoản lớn nhất"],
    horizontal=True
)

if selection_mode == "Chọn thủ công":
    selected_stocks = st.sidebar.multiselect("Chọn cổ phiếu", options=manual_stocks, default=["ACB", "VCB", "TCB", "HPG", "FPT", "MWG", "SSI"])
elif selection_mode == "Chọn 30 cổ phiếu VN30":
    vn30_list = ["ACB", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG", "MBB", "MSN", "MWG", "NVL", "PNJ", "POW", "SAB", "SSI", "STB", "TCB", "TPB", "VCB", "VHM", "VIC", "VJC", "VNM", "VPB", "VRE", "VIX", "SHB", "LPB"]
    selected_stocks = vn30_list
else:
    vn100_list = ["HPG","FPT","TCB","SSI","STB","VND","MWG","MBB","VHM","VIC","VPB","DIG","NVL","GEX","VCI","MSN","VNM","ACB","CTG","SHB","HDB","VIX","KBC","PDR","DXG","VCB","DGC","TPB","HSG","NKG","VRE","EIB","POW","GAS","LPB","TCH","VJC","BID","PLX","SAB","BVH","REE","PNJ","GVR","FRT","FTS","CTS","BSI","VHC","ANV","IDC","KDH","NLG","DBC","PVS","PVD","SCS","VOS","PVT","HAH","DCM","DPM","PC1","GEG","VGT","TNG","MSB","OCB","VIB","BAB","TTA","BCG","HDG","SAM","AAA","PHR","SZC","VPI","CII","HHV","LCG","VCG","LSS","SBT","QNS","MIG","GIL","VNA","SKG","VSC"]
    selected_stocks = vn100_list

if st.sidebar.button("🚀 Chạy phân tích Multi-View", type="primary"):
    with st.spinner("Đang phân tích..."):
        results = []
        day_factor, near_exp, days_to_exp, exp_text = get_market_context()
        
        market_data = get_market_data(selected_stocks)

        regime, market_factor = detect_market_regime(market_data)
        
        for symbol in selected_stocks:
            try:
                df = Vnstock().stock(symbol=symbol).quote.history(
                    start=(datetime.now() - timedelta(days=130)).strftime("%Y-%m-%d"),
                    end=datetime.now().strftime("%Y-%m-%d"),
                    interval="1D"
                )
                time.sleep(1.5)

                if df is None or df.empty or len(df) < 40:
                    continue

                current_price = df['close'].iloc[-1]
                support = df['low'].rolling(20).min().iloc[-1]

                view_scores = calculate_view_scores(df, current_price, support, symbol)   # Truyền symbol vào
                # tech_score = calculate_weighted_score(view_scores)
                xh_result = scan_xanh_hong_score(df, regime)
                tech_score = calculate_weighted_score_v2(view_scores, xh_result)
                final_score = round(tech_score['final_score'] + day_factor, 2)
                final_score += market_factor

                if near_exp:
                    final_score += 1.0 if days_to_exp >= 0 else 0.5
                final_score = round(min(max(final_score, 3.0), 10.5), 2)

                fib_382, fib_50, fib_618 = calculate_fibonacci(df)

                recommendation = get_recommendation(final_score, regime)

                # results.append({
                #     'Mã CK': symbol,
                #     'Giá hiện tại': round(current_price, 2),
                #     'Fib 38.2': fib_382,
                #     'Fib 50': fib_50,
                #     'Fib 61.8': fib_618,
                #     'Trend': round(view_scores.get('Trend', 0), 1),
                #     'Momentum': round(view_scores.get('Momentum', 0), 1),
                #     'Oscillator': round(view_scores.get('Oscillator', 0), 1),
                #     'Volume': round(view_scores.get('Volume', 0), 1),
                #     'Volatility': round(view_scores.get('Volatility', 0), 1),
                #     'PriceAction': round(view_scores.get('PriceAction', 0), 1),
                #     'Ichimoku': round(view_scores.get('Ichimoku', 0), 1),
                #     'Tech Score': tech_score,
                #     'Final Score': final_score,
                #     'Ngành nghề': get_sector(symbol),
                #     'Khuyến nghị': recommendation
                # })
                # ===== TÍNH X-H SCORE =====
                

                results.append({
                    'Mã CK': symbol,
                    'Giá hiện tại': round(current_price, 2),
                    'Fib 38.2': fib_382,
                    'Fib 50': fib_50,
                    'Fib 61.8': fib_618,
                    'Trend': round(view_scores.get('Trend', 0), 1),
                    'Momentum': round(view_scores.get('Momentum', 0), 1),
                    'Oscillator': round(view_scores.get('Oscillator', 0), 1),
                    'Volume': round(view_scores.get('Volume', 0), 1),
                    'Volatility': round(view_scores.get('Volatility', 0), 1),
                    'PriceAction': round(view_scores.get('PriceAction', 0), 1),
                    'Ichimoku': round(view_scores.get('Ichimoku', 0), 1),
                    # 'Tech Score': tech_score,
                    'Final Score': final_score,
                    'X-H': xh_result['score'] if isinstance(xh_result, dict) else xh_result,
                    'Ngành nghề': get_sector(symbol),
                    'Khuyến nghị': recommendation
                })
            except Exception as e:
                st.error(f"Lỗi {symbol}: {str(e)[:120]}")

        if results:
            df_result = pd.DataFrame(results)
            df_result = df_result.sort_values(by='Final Score', ascending=False).reset_index(drop=True)
            st.success(f"✅ Hoàn thành phân tích {len(results)} cổ phiếu!")
            st.subheader("🏆 Bảng Xếp Hạng Multi-View")
            st.subheader(f"🌍 Market Regime: {regime}")
            st.dataframe(
                df_result.style.background_gradient(subset=['Final Score'], cmap='RdYlGn'),
                use_container_width=True,
                height=700
            )
            filename = f"MultiView_Trade_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            df_result.to_excel(filename, index=False)
            with open(filename, "rb") as f:
                st.download_button("📥 Tải file Excel", data=f, file_name=filename)

with st.expander("📋 Hướng dẫn"):
    st.write("• Đã tích hợp Ichimoku + RSI")
    st.write("• PriceAction, Volume, Momentum đã được tối ưu")

st.caption("Multi-View Trade v6 - Đã fix lỗi BBands & Ichimoku")
