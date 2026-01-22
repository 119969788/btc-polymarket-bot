"""
市场查找与条件解析（最终可用版：按美东 15 分钟整点精确定位）
- ✅ 不再依赖 createdAt 列表（会漏掉当前 15m 场）
- ✅ 直接用美东时间算 slug: btc-updown-15m-<start_ts>
- ✅ 用 Gamma: GET /markets/slug/{slug} 精确获取市场
- ✅ 优先返回【正在进行】；没有就返回【下一场】
- ✅ 获取 UP/DOWN 的 clobTokenIds 用于 CLOB orderbook 下单
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple
import json
import time
import requests

try:
    from zoneinfo import ZoneInfo  # py3.9+
except Exception:
    ZoneInfo = None  # type: ignore

GAMMA_API = "https://gamma-api.polymarket.com"
ET_TZ = "America/New_York"
INTERVAL = 900  # 15 minutes


def _safe_bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "y"):
        return True
    if s in ("false", "0", "no", "n"):
        return False
    return default


def _parse_listish(v: Any) -> List[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        try:
            x = json.loads(s)
            return x if isinstance(x, list) else []
        except Exception:
            return [p.strip() for p in s.split(",") if p.strip()]
    return []


def _is_tradeable_market(m: Dict[str, Any]) -> bool:
    """
    15m 市场过滤：不 closed + enableOrderBook
    （active/acceptingOrders 在 Gamma 上可能延迟/为空，别用它卡死）
    """
    closed = _safe_bool(m.get("closed"), False)
    enable_ob = _safe_bool(m.get("enableOrderBook"), True)
    return (not closed) and enable_ob


def _get_market_by_slug(slug: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    Gamma: GET /markets/slug/{slug}
    """
    try:
        r = requests.get(
            f"{GAMMA_API}/markets/slug/{slug}",
            timeout=timeout,
            headers={
                "User-Agent": "btc-15m-bot/1.0",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        if r.status_code != 200:
            return None
        data = r.json()
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _et_floor_15m_start_ts(now_utc: int) -> int:
    """
    用美东时间把当前时刻 floor 到 15 分钟整点，然后转回 UTC timestamp（作为 slug ts）
    """
    if ZoneInfo is None:
        # 兜底：不用 tz，直接按 UTC floor（不推荐，但保证不崩）
        return (now_utc // INTERVAL) * INTERVAL

    from datetime import datetime, timezone

    dt_utc = datetime.fromtimestamp(now_utc, tz=timezone.utc)
    dt_et = dt_utc.astimezone(ZoneInfo(ET_TZ))

    # floor 到 15 分钟
    minute = (dt_et.minute // 15) * 15
    dt_floor = dt_et.replace(minute=minute, second=0, microsecond=0)

    # 转回 UTC ts
    dt_floor_utc = dt_floor.astimezone(timezone.utc)
    return int(dt_floor_utc.timestamp())


def _build_slug(ts: int) -> str:
    return f"btc-updown-15m-{ts}"


def find_btc_15min_market(host: str, forward_steps: int = 12, backward_steps: int = 4) -> Optional[Dict[str, Any]]:
    """
    返回：
    {
      "market_id": int,
      "question": str,
      "slug": str,
      "start_ts": int,
      "end_ts": int,
      "is_live": bool
    }

    逻辑：
    1) 先算出“当前美东 15m 场”的 start_ts（floor）
    2) 优先查：上一场 / 当前场 / 下一场
    3) 再查：未来 forward_steps 场、过去 backward_steps 场
    4) 优先返回 live；否则返回 next（最接近未来的）
    """
    now = int(time.time())
    base_ts = _et_floor_15m_start_ts(now)

    # 优先探测：上一场/当前场/下一场（保证能抓到你给的 1769046300 这种）
    probe_ts = [base_ts - INTERVAL, base_ts, base_ts + INTERVAL]

    # 扩展探测：未来/过去更多场（避免刚好卡边界）
    for i in range(2, forward_steps + 1):
        probe_ts.append(base_ts + i * INTERVAL)
    for i in range(2, backward_steps + 1):
        probe_ts.append(base_ts - i * INTERVAL)

    # 去重并排序（先查离现在近的）
    uniq = sorted(set(probe_ts), key=lambda t: abs(t - now))

    live_pick: Optional[Tuple[int, Dict[str, Any]]] = None
    next_pick: Optional[Tuple[int, Dict[str, Any]]] = None

    for ts in uniq:
        slug = _build_slug(ts)
        m = _get_market_by_slug(slug)
        if not m:
            continue
        if not _is_tradeable_market(m):
            continue

        # 统一提取 market_id
        mid = m.get("id") or m.get("market_id") or m.get("marketId")
        if mid is None:
            continue

        start_ts = ts
        end_ts = ts + INTERVAL
        is_live = (start_ts <= now < end_ts)

        pack = {
            "market_id": int(mid),
            "question": m.get("question") or m.get("title") or slug,
            "slug": slug,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "is_live": is_live,
        }

        if is_live:
            # 选最新正在进行的（start_ts 最大）
            if (live_pick is None) or (start_ts > live_pick[0]):
                live_pick = (start_ts, pack)
        else:
            # 选最近未来的一场（start_ts 最小且 > now）
            if start_ts > now:
                if (next_pick is None) or (start_ts < next_pick[0]):
                    next_pick = (start_ts, pack)

    if live_pick:
        return live_pick[1]
    if next_pick:
        return next_pick[1]
    return None


def get_market_conditions(host: str, market_id: int) -> Optional[Dict[str, str]]:
    """
    获取 market_id 的 UP/DOWN clobTokenIds
    返回：{"UP": "<token_id>", "DOWN": "<token_id>"}
    """
    try:
        r = requests.get(
            f"{GAMMA_API}/markets/{market_id}",
            timeout=10,
            headers={
                "User-Agent": "btc-15m-bot/1.0",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        r.raise_for_status()
        m = r.json() if isinstance(r.json(), dict) else {}
    except Exception:
        return None

    outcomes = _parse_listish(m.get("outcomes") or m.get("shortOutcomes"))
    token_ids = _parse_listish(m.get("clobTokenIds"))

    if len(outcomes) >= 2 and len(token_ids) >= 2:
        out_map: Dict[str, str] = {}
        for name, tid in zip(outcomes, token_ids):
            n = str(name).strip().lower()
            if n == "up":
                out_map["UP"] = str(tid)
            elif n == "down":
                out_map["DOWN"] = str(tid)
        if "UP" in out_map and "DOWN" in out_map:
            return out_map

    # 兼容 tokens 列表结构
    tokens = m.get("tokens")
    if isinstance(tokens, list):
        out_map: Dict[str, str] = {}
        for t in tokens:
            name = (t.get("outcome") or t.get("name") or "").strip().lower()
            tid = t.get("clobTokenId") or t.get("tokenId") or t.get("id")
            if not tid:
                continue
            if name == "up":
                out_map["UP"] = str(tid)
            elif name == "down":
                out_map["DOWN"] = str(tid)
        if "UP" in out_map and "DOWN" in out_map:
            return out_map

    return None
