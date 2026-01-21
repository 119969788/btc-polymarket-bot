"""市场查找模块"""
import requests
import time
from typing import Optional

def find_btc_15min_market(host: str = "https://clob.polymarket.com") -> Optional[dict]:
    """
    查找当前活跃的BTC 15分钟市场
    
    BTC 15分钟市场的slug格式: btc-updown-15m-{unix_epoch}
    其中epoch是市场结束时间的UNIX时间戳（秒级）
    
    Returns:
        dict: 市场信息，包含market_id, question等
    """
    try:
        # 方法1: 根据当前时间生成slug并查询
        # BTC 15分钟市场每15分钟一个，结束时间是下一个15分钟的整点
        current_time = int(time.time())
        # 计算下一个15分钟的整点时间戳
        next_15min = ((current_time // 900) + 1) * 900  # 900秒 = 15分钟
        
        # 尝试当前和下一个15分钟的市场
        time_slots = [next_15min, next_15min - 900, next_15min - 1800]
        
        for epoch in time_slots:
            slug = f"btc-updown-15m-{epoch}"
            
            # 尝试使用Gamma API（Polymarket的公开API）
            try:
                gamma_url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
                response = requests.get(gamma_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        market = data[0]
                        if market.get("active", True):
                            return {
                                "market_id": market.get("id") or market.get("clobTokenId"),
                                "question": market.get("question"),
                                "slug": market.get("slug"),
                                "active": market.get("active", True),
                                "end_date": market.get("endDate")
                            }
            except Exception as e:
                pass
        
        # 方法2: 使用CLOB API搜索所有市场
        try:
            url = f"{host}/markets"
            headers = {"Accept": "application/json"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                markets = response.json()
                
                # 查找BTC 15分钟市场
                if isinstance(markets, list):
                    for market in markets:
                        slug = str(market.get("slug", "")).lower()
                        question = str(market.get("question", "")).lower()
                        
                        # 检查是否是BTC 15分钟市场
                        if ("btc-updown-15m" in slug or 
                            (("bitcoin" in question or "btc" in question) and 
                             ("15" in question or "15m" in question or "15min" in question))):
                            if market.get("active", True):
                                return {
                                    "market_id": market.get("id") or market.get("market_id") or market.get("clobTokenId"),
                                    "question": market.get("question"),
                                    "slug": market.get("slug"),
                                    "active": market.get("active", True)
                                }
        except Exception as e:
            pass
        
        # 方法3: 使用Gamma API搜索所有BTC市场
        try:
            gamma_url = "https://gamma-api.polymarket.com/markets?category=crypto&limit=100"
            response = requests.get(gamma_url, timeout=10)
            if response.status_code == 200:
                markets = response.json()
                if isinstance(markets, list):
                    for market in markets:
                        slug = str(market.get("slug", "")).lower()
                        if "btc-updown-15m" in slug:
                            if market.get("active", True):
                                return {
                                    "market_id": market.get("id") or market.get("clobTokenId"),
                                    "question": market.get("question"),
                                    "slug": market.get("slug"),
                                    "active": market.get("active", True),
                                    "end_date": market.get("endDate")
                                }
        except Exception as e:
            pass
        
        return None
    except Exception as e:
        print(f"❌ 查找市场时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_market_conditions(host: str, market_id: str) -> Optional[dict]:
    """
    获取市场条件（UP/DOWN）
    
    Returns:
        dict: 包含UP和DOWN条件ID的字典
    """
    try:
        url = f"{host}/markets/{market_id}/conditions"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        conditions = response.json() if response.headers.get("content-type", "").startswith("application/json") else None
        
        if not conditions:
            return None
        
        result = {}
        if isinstance(conditions, list):
            for condition in conditions:
                outcome = str(condition.get("outcome", "")).upper()
                condition_id = condition.get("id") or condition.get("token_id")
                if condition_id:
                    if "UP" in outcome or "上涨" in outcome or "上升" in outcome or "YES" in outcome:
                        result["UP"] = condition_id
                    elif "DOWN" in outcome or "下跌" in outcome or "下降" in outcome or "NO" in outcome:
                        result["DOWN"] = condition_id
        elif isinstance(conditions, dict):
            # 单个条件对象
            outcome = str(conditions.get("outcome", "")).upper()
            condition_id = conditions.get("id") or conditions.get("token_id")
            if condition_id:
                if "UP" in outcome or "YES" in outcome:
                    result["UP"] = condition_id
                elif "DOWN" in outcome or "NO" in outcome:
                    result["DOWN"] = condition_id
        
        return result if len(result) == 2 else None
    except Exception as e:
        print(f"❌ 获取市场条件时出错: {e}")
        print("   提示: 如果API端点不正确，可能需要使用py-clob-client的条件查询功能")
        return None
