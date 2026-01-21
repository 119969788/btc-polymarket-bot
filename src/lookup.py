"""市场查找模块"""
import requests
from typing import Optional

def find_btc_15min_market(host: str = "https://clob.polymarket.com") -> Optional[dict]:
    """
    查找当前活跃的BTC 15分钟市场
    
    Returns:
        dict: 市场信息，包含market_id, question等
    """
    try:
        # 使用Polymarket CLOB API获取市场信息
        # 注意：实际API可能需要使用py-clob-client，这里使用简化的HTTP请求
        url = f"{host}/markets"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 尝试解析响应
        if response.headers.get("content-type", "").startswith("application/json"):
            markets = response.json()
        else:
            # 如果不是JSON，可能需要使用py-clob-client
            print("⚠️  直接HTTP请求可能不适用，建议使用py-clob-client")
            return None
        
        # 查找BTC 15分钟市场
        if isinstance(markets, list):
            for market in markets:
                question = str(market.get("question", "")).lower()
                if ("bitcoin" in question or "btc" in question) and ("15" in question or "15m" in question or "15min" in question):
                    if market.get("active", True):  # 默认认为活跃
                        return {
                            "market_id": market.get("id") or market.get("market_id"),
                            "question": market.get("question"),
                            "slug": market.get("slug"),
                            "active": market.get("active", True)
                        }
        elif isinstance(markets, dict):
            # 如果返回的是单个市场对象
            question = str(markets.get("question", "")).lower()
            if ("bitcoin" in question or "btc" in question) and ("15" in question or "15m" in question or "15min" in question):
                return {
                    "market_id": markets.get("id") or markets.get("market_id"),
                    "question": markets.get("question"),
                    "slug": markets.get("slug"),
                    "active": markets.get("active", True)
                }
        
        return None
    except Exception as e:
        print(f"❌ 查找市场时出错: {e}")
        print("   提示: 如果API端点不正确，可能需要使用py-clob-client的market查询功能")
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
