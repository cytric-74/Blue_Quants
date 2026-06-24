import json
import math
import time
import threading
from datetime import datetime, timezone

import yfinance as yf
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

DEFAULT_TICKERS = ["NVDA", "AMD", "TSLA", "JPM"]

CARD_COLORS = {
    0: "sage",
    1: "sienna",
    2: "rose",
    3: "lavender",
}

_CACHE = {}
_CACHE_LOCK = threading.Lock()
_INFO_TTL = 90
_HIST_TTL = 150
_NEWS_TTL = 300


def _cache_get(key):
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry and time.time() - entry["ts"] < entry["ttl"]:
            return entry["data"]
    return None


def _cache_set(key, data, ttl):
    with _CACHE_LOCK:
        _CACHE[key] = {"data": data, "ts": time.time(), "ttl": ttl}


def _fetch_with_retry(fn, retries=2, delay=1.5):
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as e:
            if attempt == retries:
                raise e
            time.sleep(delay * (attempt + 1))
    return None


def _get_ticker_info(ticker_sym):
    key = f"info:{ticker_sym}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    info = _fetch_with_retry(lambda: yf.Ticker(ticker_sym).info)
    if info:
        _cache_set(key, info, _INFO_TTL)
    return info or {}


def _get_ticker_history(ticker_sym, period="5d", interval="1h"):
    key = f"hist:{ticker_sym}:{period}:{interval}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    hist = _fetch_with_retry(lambda: yf.Ticker(ticker_sym).history(period=period, interval=interval))
    if hist is not None:
        _cache_set(key, hist, _HIST_TTL)
    return hist


def _get_ticker_news(ticker_sym):
    key = f"news:{ticker_sym}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    news = _fetch_with_retry(lambda: yf.Ticker(ticker_sym).news)
    _cache_set(key, news or [], _NEWS_TTL)
    return news or []


def _get_ticker_options(ticker_sym):
    key = f"options:{ticker_sym}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    tk = yf.Ticker(ticker_sym)
    exps = _fetch_with_retry(lambda: tk.options)
    _cache_set(key, exps or [], _HIST_TTL)
    return exps or []


def _safe_float(val, digits=2):
    try:
        v = float(val)
        return round(v, digits) if not math.isnan(v) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _safe_int(val):
    try:
        v = int(val)
        return v if not math.isnan(float(val)) else 0
    except (TypeError, ValueError):
        return 0


def _pct_change(current, previous):
    if previous and previous != 0:
        return round((current - previous) / abs(previous) * 100, 2)
    return 0.0


def _driver_attribution(info, hist):
    drivers = []

    avg_vol = _safe_float(info.get("averageVolume", 0))
    today_vol = _safe_float(info.get("volume", 0))
    vol_ratio = (today_vol / avg_vol) if avg_vol > 0 else 1.0
    vol_score = min(int(vol_ratio * 12), 30)
    drivers.append({
        "name": "Volume Expansion",
        "value": vol_score,
        "evidence": f"Volume running at {vol_ratio:.1f}× the 20-day average ({int(today_vol/1e6):.0f}M shares).",
        "icon": "volume"
    })

    target = _safe_float(info.get("targetMeanPrice", 0))
    current = _safe_float(info.get("currentPrice", 0) or info.get("regularMarketPrice", 0))
    upside = ((target - current) / current * 100) if current > 0 and target > 0 else 0
    earn_score = min(max(int(abs(upside) * 1.5), 5), 35)
    drivers.append({
        "name": "Analyst Price Target",
        "value": earn_score,
        "evidence": f"Consensus target ${target:.2f} implies {upside:+.1f}% upside from current price.",
        "icon": "target"
    })

    beta = _safe_float(info.get("beta", 1.0))
    beta_score = min(max(int(beta * 10), 8), 25)
    drivers.append({
        "name": "Market Beta Exposure",
        "value": beta_score,
        "evidence": f"β={beta:.2f} — {'amplifies' if beta > 1 else 'dampens'} broad market moves.",
        "icon": "beta"
    })

    short_pct = _safe_float(info.get("shortPercentOfFloat", 0)) * 100
    short_score = min(int(short_pct * 1.2), 20)
    drivers.append({
        "name": "Short Interest Pressure",
        "value": short_score,
        "evidence": f"{short_pct:.1f}% of float is sold short — {'elevated squeeze risk' if short_pct > 10 else 'moderate pressure'}.",
        "icon": "short"
    })

    inst_pct = _safe_float(info.get("institutionalOwnershipPercentage", 0) or info.get("heldPercentInstitutions", 0)) * 100
    inst_score = min(max(int(inst_pct * 0.15), 5), 15)
    drivers.append({
        "name": "Institutional Conviction",
        "value": inst_score,
        "evidence": f"Institutions hold {inst_pct:.1f}% of outstanding shares.",
        "icon": "institution"
    })

    total = sum(d["value"] for d in drivers) or 1
    for d in drivers:
        d["value"] = round(d["value"] / total * 100)

    drivers.sort(key=lambda x: x["value"], reverse=True)
    return drivers


def _intelligence_metrics(info):
    beta = _safe_float(info.get("beta", 1.0))
    short_pct = _safe_float(info.get("shortPercentOfFloat", 0)) * 100
    inst_pct = _safe_float(info.get("heldPercentInstitutions", 0) or 0) * 100
    profit_m = _safe_float(info.get("profitMargins", 0)) * 100
    rev_growth = _safe_float(info.get("revenueGrowth", 0)) * 100
    gross_m = _safe_float(info.get("grossMargins", 0)) * 100

    return [
        {"label": "Momentum Heat", "value": min(int(beta * 55), 99),
         "note": f"Beta {beta:.2f} — price sensitivity vs. S&P 500."},
        {"label": "Institutional Conviction", "value": min(int(inst_pct), 99),
         "note": f"{inst_pct:.1f}% held by institutions. High = smart-money backing."},
        {"label": "Short Squeeze Risk", "value": min(int(short_pct * 4), 99),
         "note": f"{short_pct:.1f}% of float short. Spike can trigger rapid covering."},
        {"label": "Profit Margin Quality", "value": min(max(int(profit_m), 0), 99),
         "note": f"Net margin {profit_m:.1f}% — {'strong' if profit_m > 15 else 'moderate' if profit_m > 0 else 'negative'} profitability."},
        {"label": "Revenue Growth", "value": min(max(int(rev_growth + 50), 0), 99),
         "note": f"YoY revenue growth {rev_growth:+.1f}%."},
        {"label": "Gross Margin Strength", "value": min(int(gross_m), 99),
         "note": f"Gross margin {gross_m:.1f}% — {'premium' if gross_m > 60 else 'healthy' if gross_m > 30 else 'thin'} business model."},
    ]


def _generate_suggestion(info, drivers, change_pct):
    price = _safe_float(info.get("currentPrice", 0) or info.get("regularMarketPrice", 0))
    target = _safe_float(info.get("targetMeanPrice", 0))
    beta = _safe_float(info.get("beta", 1.0))
    short_pct = _safe_float(info.get("shortPercentOfFloat", 0)) * 100
    avg_vol = _safe_float(info.get("averageVolume", 0))
    today_vol = _safe_float(info.get("volume", 0))
    vol_ratio = (today_vol / avg_vol) if avg_vol > 0 else 1.0
    inst_pct = _safe_float(info.get("heldPercentInstitutions", 0) or 0) * 100
    profit_m = _safe_float(info.get("profitMargins", 0)) * 100

    upside = ((target - price) / price * 100) if price > 0 and target > 0 else 0
    primary_driver = drivers[0]["name"] if drivers else "Market Movement"

    signals = []
    if vol_ratio > 2.0:
        signals.append("heavy_volume")
    if short_pct > 15:
        signals.append("squeeze_risk")
    if upside > 15:
        signals.append("undervalued")
    elif upside < -10:
        signals.append("overvalued")
    if inst_pct > 70:
        signals.append("strong_institutional")
    if beta > 1.5:
        signals.append("high_volatility")
    if profit_m > 20:
        signals.append("profitable")
    elif profit_m < 0:
        signals.append("unprofitable")

    change = abs(change_pct)
    is_up = change_pct >= 0

    if "squeeze_risk" in signals and "heavy_volume" in signals:
        action = "High Alert"
        stance = "caution"
        headline = "Short squeeze conditions detected"
        detail = f"With {short_pct:.1f}% short interest and volume at {vol_ratio:.1f}× average, a squeeze may drive extreme moves. Use tight stop-losses and avoid chasing."
        what_to_do = "Set alerts for breakout levels. If long, trail stops aggressively. Avoid opening new large positions until volume normalises."
    elif "undervalued" in signals and "strong_institutional" in signals:
        action = "Opportunity"
        stance = "bullish"
        headline = "Institutional backing with upside potential"
        detail = f"Analyst consensus implies {upside:+.1f}% upside, backed by {inst_pct:.0f}% institutional ownership. Smart money is positioned here."
        what_to_do = "Consider building a position on pullbacks. This has strong fundamental backing — accumulate in tranches rather than all at once."
    elif "overvalued" in signals:
        action = "Watch"
        stance = "bearish"
        headline = "Trading above analyst consensus"
        detail = f"Price has run past the ${target:.0f} consensus target by {abs(upside):.1f}%. Momentum can persist but risk/reward is stretched."
        what_to_do = "Take partial profits if you're in a position. New entries are risky here — wait for a pullback to the target range before adding."
    elif "heavy_volume" in signals and is_up:
        action = "Momentum"
        stance = "bullish"
        headline = "Strong volume-driven breakout"
        detail = f"Volume is running {vol_ratio:.1f}× the 20-day average on a {change_pct:+.2f}% move. This suggests real conviction behind the move."
        what_to_do = "Momentum is confirmed by volume. Consider entering with a stop below today's low. Trail your stop as the move extends."
    elif "heavy_volume" in signals and not is_up:
        action = "Caution"
        stance = "bearish"
        headline = "High-volume selloff in progress"
        detail = f"Volume at {vol_ratio:.1f}× average on a {change_pct:+.2f}% decline signals institutional selling pressure."
        what_to_do = "Avoid catching the falling knife. Wait for volume to dry up and price to stabilise before considering entry. If holding, review your stop-loss."
    elif "high_volatility" in signals:
        action = "Volatile"
        stance = "caution"
        headline = f"High-beta stock amplifying market moves"
        detail = f"β={beta:.2f} means this stock moves {beta:.1f}× the market. Today's {change_pct:+.2f}% move is {'amplified' if change > 1 else 'muted'} vs. the index."
        what_to_do = "Size your position smaller than usual. High-beta names require wider stops — use 1.5-2× your normal stop distance."
    elif "profitable" in signals and "strong_institutional" in signals:
        action = "Quality"
        stance = "bullish"
        headline = "Strong fundamentals with smart-money backing"
        detail = f"{profit_m:.1f}% profit margins and {inst_pct:.0f}% institutional ownership indicate a quality business."
        what_to_do = "This is a core holding candidate. Build positions during market weakness rather than chasing green days."
    else:
        if is_up and change > 1:
            action = "Trending Up"
            stance = "bullish"
            headline = f"Positive momentum — {primary_driver} leading"
            detail = f"The stock is up {change_pct:+.2f}% driven primarily by {primary_driver.lower()}. Monitor for continuation."
            what_to_do = "The move looks constructive. Consider entering on an intraday pullback with a stop below the session low."
        elif not is_up and change > 1:
            action = "Pullback"
            stance = "bearish"
            headline = f"Under pressure — {primary_driver} weighing"
            detail = f"Down {change_pct:+.2f}%, primarily from {primary_driver.lower()}. Assess whether this is a buying opportunity or the start of a trend."
            what_to_do = "Wait for price to find support before acting. Watch for a reversal candle with decreasing volume as a potential entry signal."
        else:
            action = "Hold Steady"
            stance = "neutral"
            headline = "Low volatility — consolidating"
            detail = f"The stock is moving {change_pct:+.2f}% with no major catalyst. This is a consolidation phase."
            what_to_do = "No action required right now. Set price alerts above and below the current range to catch the next breakout."

    return {
        "action": action,
        "stance": stance,
        "headline": headline,
        "detail": detail,
        "what_to_do": what_to_do,
        "primary_driver": primary_driver,
    }


def _build_stock_card(ticker_sym, idx=0):
    try:
        info = _get_ticker_info(ticker_sym)

        price = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0))
        prev = _safe_float(info.get("previousClose") or info.get("regularMarketPreviousClose", price))
        change_pct = _pct_change(price, prev)
        change_abs = round(price - prev, 2)

        hist = _get_ticker_history(ticker_sym, period="5d", interval="1h")
        sparkline = []
        if hist is not None and not hist.empty:
            closes = hist["Close"].dropna().tolist()
            sparkline = [round(c, 2) for c in closes[-24:]]

        volume = _safe_int(info.get("volume", 0))
        avg_vol = _safe_int(info.get("averageVolume", 1))
        vol_ratio = round(volume / avg_vol, 1) if avg_vol > 0 else 1.0

        market_cap = info.get("marketCap", 0)
        if market_cap >= 1e12:
            mc_str = f"${market_cap/1e12:.2f}T"
        elif market_cap >= 1e9:
            mc_str = f"${market_cap/1e9:.1f}B"
        else:
            mc_str = f"${market_cap/1e6:.0f}M"

        conf = min(max(int(
            (min(vol_ratio * 20, 40)) +
            (30 if abs(change_pct) > 2 else 15) +
            (30 if _safe_float(info.get("heldPercentInstitutions", 0)) > 0.5 else 15)
        ), 30), 97)

        drivers = _driver_attribution(info, hist)
        suggestion = _generate_suggestion(info, drivers, change_pct)

        return {
            "ticker": ticker_sym.upper(),
            "name": info.get("longName") or info.get("shortName") or ticker_sym,
            "price": f"{price:,.2f}",
            "change_pct": f"{change_pct:+.2f}",
            "change_abs": f"{change_abs:+.2f}",
            "is_positive": change_pct >= 0,
            "confidence": conf,
            "sector": info.get("sector", "—"),
            "industry": info.get("industry", "—"),
            "market_cap": mc_str,
            "volume": f"{volume/1e6:.1f}M",
            "avg_volume": f"{avg_vol/1e6:.1f}M",
            "vol_ratio": f"{vol_ratio}x avg",
            "primary_driver": drivers[0]["name"] if drivers else "Market Movement",
            "sparkline": sparkline,
            "color": CARD_COLORS.get(idx % 4, "lavender"),
            "drivers": drivers,
            "intelligence_metrics": _intelligence_metrics(info),
            "suggestion": suggestion,
            "pe_ratio": _safe_float(info.get("trailingPE", 0)),
            "52w_high": _safe_float(info.get("fiftyTwoWeekHigh", 0)),
            "52w_low": _safe_float(info.get("fiftyTwoWeekLow", 0)),
            "beta": _safe_float(info.get("beta", 0)),
            "dividend_yield": round(_safe_float(info.get("dividendYield", 0)) * 100, 2),
        }
    except Exception as e:
        return {
            "ticker": ticker_sym.upper(),
            "name": ticker_sym.upper(),
            "price": "0.00", "change_pct": "+0.00", "change_abs": "+0.00",
            "is_positive": True, "confidence": 0, "sector": "—", "industry": "—",
            "market_cap": "—", "volume": "—", "avg_volume": "—",
            "vol_ratio": "—", "primary_driver": "Data unavailable",
            "sparkline": [], "color": CARD_COLORS.get(idx % 4, "lavender"),
            "drivers": [], "intelligence_metrics": [],
            "suggestion": {"action": "Unavailable", "stance": "neutral", "headline": "Data fetch failed", "detail": str(e), "what_to_do": "Try refreshing in a moment.", "primary_driver": "—"},
            "pe_ratio": 0, "52w_high": 0, "52w_low": 0, "beta": 0, "dividend_yield": 0,
            "error": str(e),
        }


def index(request):
    tickers = request.GET.getlist("t") or DEFAULT_TICKERS
    tickers = [t.upper().strip() for t in tickers[:6]]

    stocks = [_build_stock_card(t, i) for i, t in enumerate(tickers)]
    primary = stocks[0] if stocks else {}

    context = {
        "active_page": "dashboard",
        "stocks": stocks,
        "profile": primary,
        "tickers_json": json.dumps(tickers),
        "default_tickers": ",".join(DEFAULT_TICKERS),
    }
    return render(request, "index.html", context)


def compare_page(request):
    tickers = request.GET.getlist("t") or DEFAULT_TICKERS
    tickers = [t.upper().strip() for t in tickers[:6]]
    context = {
        "active_page": "compare",
        "tickers_json": json.dumps(tickers),
        "default_tickers": ",".join(DEFAULT_TICKERS),
    }
    return render(request, "compare.html", context)


def options_page(request):
    ticker_sym = request.GET.get("t", "NVDA").upper()
    context = {
        "active_page": "options",
        "ticker": ticker_sym,
        "tickers_json": json.dumps(DEFAULT_TICKERS),
        "default_tickers": ",".join(DEFAULT_TICKERS),
    }
    return render(request, "options.html", context)


@require_GET
def api_stock(request, ticker_sym):
    ticker_sym = ticker_sym.upper()
    data = _build_stock_card(ticker_sym)
    return JsonResponse(data)


@require_GET
def api_compare(request):
    tickers = request.GET.getlist("t")
    if not tickers:
        tickers = DEFAULT_TICKERS
    tickers = [t.upper().strip() for t in tickers[:6]]

    result = {}
    for t in tickers:
        try:
            period = request.GET.get("period", "1mo")
            interval = "1d"
            if period == "1d":
                interval = "5m"
            elif period == "5d":
                interval = "15m"

            hist = _get_ticker_history(t, period=period, interval=interval)
            if hist is None or hist.empty:
                result[t] = {"labels": [], "prices": [], "error": "No data"}
                continue

            closes = hist["Close"].dropna()
            labels = [str(idx.strftime("%Y-%m-%d %H:%M") if interval in ("5m", "15m")
                        else idx.strftime("%b %d")) for idx in closes.index]

            base = closes.iloc[0]
            normalised = [round((c / base) * 100, 2) for c in closes.tolist()]

            result[t] = {
                "labels": labels,
                "prices": [round(c, 2) for c in closes.tolist()],
                "normalised": normalised,
            }
        except Exception as e:
            result[t] = {"labels": [], "prices": [], "error": str(e)}

    return JsonResponse(result)


@require_GET
def api_options(request, ticker_sym):
    ticker_sym = ticker_sym.upper()
    try:
        exps = _get_ticker_options(ticker_sym)

        if not exps:
            return JsonResponse({"error": "No options data available", "ticker": ticker_sym})

        expiry = request.GET.get("expiry", exps[0])
        if expiry not in exps:
            expiry = exps[0]

        tk = yf.Ticker(ticker_sym)
        chain = _fetch_with_retry(lambda: tk.option_chain(expiry))

        def _chain_to_list(df, option_type):
            rows = []
            for _, row in df.head(15).iterrows():
                rows.append({
                    "strike": _safe_float(row.get("strike", 0)),
                    "lastPrice": _safe_float(row.get("lastPrice", 0)),
                    "bid": _safe_float(row.get("bid", 0)),
                    "ask": _safe_float(row.get("ask", 0)),
                    "volume": _safe_int(row.get("volume", 0)),
                    "openInterest": _safe_int(row.get("openInterest", 0)),
                    "impliedVolatility": round(_safe_float(row.get("impliedVolatility", 0)) * 100, 1),
                    "inTheMoney": bool(row.get("inTheMoney", False)),
                    "type": option_type,
                })
            return rows

        calls = _chain_to_list(chain.calls, "call")
        puts = _chain_to_list(chain.puts, "put")

        total_call_oi = sum(c["openInterest"] for c in calls)
        total_put_oi = sum(p["openInterest"] for p in puts)
        total_oi = total_call_oi + total_put_oi
        pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0

        return JsonResponse({
            "ticker": ticker_sym,
            "expiry": expiry,
            "available_expiries": list(exps[:8]),
            "calls": calls,
            "puts": puts,
            "summary": {
                "call_oi": total_call_oi,
                "put_oi": total_put_oi,
                "put_call_ratio": pcr,
                "sentiment": "Bullish" if pcr < 0.7 else "Bearish" if pcr > 1.2 else "Neutral",
                "call_pct": round(total_call_oi / total_oi * 100, 1) if total_oi > 0 else 0,
                "put_pct": round(total_put_oi / total_oi * 100, 1) if total_oi > 0 else 0,
            }
        })
    except Exception as e:
        return JsonResponse({"error": str(e), "ticker": ticker_sym}, status=500)


@require_GET
def api_news(request, ticker_sym):
    ticker_sym = ticker_sym.upper()
    try:
        news_raw = _get_ticker_news(ticker_sym)
        news = []
        for item in news_raw[:10]:
            content = item.get("content", {})
            if not content:
                continue
            pub_date = content.get("pubDate", "")
            try:
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                diff = now - dt
                hrs = int(diff.total_seconds() / 3600)
                time_ago = f"{hrs}h ago" if hrs < 24 else f"{diff.days}d ago"
            except Exception:
                time_ago = pub_date[:10] if pub_date else "—"

            provider = content.get("provider", {})
            news.append({
                "title": content.get("title", "—"),
                "source": provider.get("displayName", "Unknown") if isinstance(provider, dict) else str(provider),
                "url": content.get("canonicalUrl", {}).get("url", "#") if isinstance(content.get("canonicalUrl"), dict) else "#",
                "time_ago": time_ago,
                "summary": content.get("summary", ""),
            })
        return JsonResponse({"ticker": ticker_sym, "news": news})
    except Exception as e:
        return JsonResponse({"ticker": ticker_sym, "news": [], "error": str(e)})


@require_GET
def api_sparkline(request, ticker_sym):
    ticker_sym = ticker_sym.upper()
    try:
        hist = _get_ticker_history(ticker_sym, period="5d", interval="30m")
        if hist is None or hist.empty:
            return JsonResponse({"ticker": ticker_sym, "data": []})
        closes = hist["Close"].dropna().tolist()
        return JsonResponse({"ticker": ticker_sym, "data": [round(c, 2) for c in closes]})
    except Exception as e:
        return JsonResponse({"ticker": ticker_sym, "data": [], "error": str(e)})
