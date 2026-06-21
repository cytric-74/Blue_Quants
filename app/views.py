from django.shortcuts import render


MARKET_SNAPSHOT = [
    {
        "ticker": "NVDA",
        "name": "NVIDIA",
        "price": "142.76",
        "change": "+4.82%",
        "confidence": 87,
        "primary_driver": "Earnings guidance revision",
        "sector": "Semiconductors",
        "volume": "2.8x avg",
    },
    {
        "ticker": "AMD",
        "name": "Advanced Micro Devices",
        "price": "164.20",
        "change": "+2.94%",
        "confidence": 78,
        "primary_driver": "Sector sympathy and options flow",
        "sector": "Semiconductors",
        "volume": "1.9x avg",
    },
    {
        "ticker": "TSLA",
        "name": "Tesla",
        "price": "231.48",
        "change": "-1.36%",
        "confidence": 72,
        "primary_driver": "Margin concern after delivery mix",
        "sector": "Automobiles",
        "volume": "1.4x avg",
    },
    {
        "ticker": "JPM",
        "name": "JPMorgan Chase",
        "price": "204.11",
        "change": "+0.88%",
        "confidence": 69,
        "primary_driver": "Yield curve steepening",
        "sector": "Financials",
        "volume": "1.1x avg",
    },
]

STOCK_PROFILES = {
    "NVDA": {
        "ticker": "NVDA",
        "name": "NVIDIA Corporation",
        "price": "142.76",
        "change": "+4.82%",
        "confidence": 87,
        "sector": "Semiconductors",
        "industry": "Accelerated Computing",
        "market_cap": "$3.51T",
        "volume": "68.4M",
        "primary_driver": "Earnings guidance revision",
        "expected_move": "+2.1% to +5.6%",
        "actual_move": "+4.8%",
    },
    "AMD": {
        "ticker": "AMD",
        "name": "Advanced Micro Devices, Inc.",
        "price": "164.20",
        "change": "+2.94%",
        "confidence": 78,
        "sector": "Semiconductors",
        "industry": "Processors and Data Center",
        "market_cap": "$265B",
        "volume": "44.8M",
        "primary_driver": "Sector sympathy and options flow",
        "expected_move": "+1.0% to +3.4%",
        "actual_move": "+2.9%",
    },
    "TSLA": {
        "ticker": "TSLA",
        "name": "Tesla, Inc.",
        "price": "231.48",
        "change": "-1.36%",
        "confidence": 72,
        "sector": "Automobiles",
        "industry": "Electric Vehicles",
        "market_cap": "$738B",
        "volume": "79.1M",
        "primary_driver": "Margin concern after delivery mix",
        "expected_move": "-2.8% to +1.2%",
        "actual_move": "-1.4%",
    },
}

DEFAULT_PROFILE = STOCK_PROFILES["NVDA"]

DRIVERS = [
    {"name": "Earnings Guidance", "value": 34, "evidence": "Revenue guide revised above consensus by 6.1%."},
    {"name": "Sector Momentum", "value": 28, "evidence": "Semiconductor peer basket advanced 2.4%."},
    {"name": "Volume Expansion", "value": 17, "evidence": "First-hour turnover ran 2.8x the 20-day average."},
    {"name": "Technical Breakout", "value": 13, "evidence": "Price cleared the 20-session resistance band."},
    {"name": "Institutional Flow", "value": 8, "evidence": "Large-lot prints concentrated near session highs."},
]

TIMELINE = [
    {"time": "09:15", "title": "Market open", "detail": "Gap opened above prior value area with elevated pre-market volume."},
    {"time": "09:42", "title": "Volume spike", "detail": "One-minute volume reached 4.1x baseline after guidance headlines circulated."},
    {"time": "09:58", "title": "News confirmed", "detail": "Financial news cluster shifted from neutral to positive."},
    {"time": "10:03", "title": "Sector rally", "detail": "Semiconductor basket breadth crossed 72% advancing constituents."},
    {"time": "10:09", "title": "Breakout", "detail": "Price moved through resistance with VWAP support intact."},
    {"time": "10:17", "title": "Momentum acceleration", "detail": "Short-horizon trend and options activity aligned."},
]

SENTIMENT = [
    {"source": "Financial News", "score": 42, "count": "12 articles"},
    {"source": "Analyst Reports", "score": 24, "count": "4 revisions"},
    {"source": "Institutional Commentary", "score": 18, "count": "3 notes"},
    {"source": "Social Media", "score": 16, "count": "31K mentions"},
]

SIMILAR_EVENTS = [
    {"ticker": "NVDA", "date": "May 2024", "score": 92, "outcome": "+6.3% next 5 sessions"},
    {"ticker": "AVGO", "date": "Mar 2025", "score": 86, "outcome": "+3.9% next 5 sessions"},
    {"ticker": "AMD", "date": "Jul 2025", "score": 81, "outcome": "+2.8% next 5 sessions"},
]

INTELLIGENCE_METRICS = [
    {"label": "Momentum Heat", "value": 84, "note": "Trend persistence across 5m, 15m, and 1h windows."},
    {"label": "Institutional Conviction", "value": 71, "note": "Large-lot activity concentrated above VWAP."},
    {"label": "News Pressure", "value": 76, "note": "Positive article velocity exceeded 30-day baseline."},
    {"label": "Retail Attention", "value": 68, "note": "Mention growth elevated, but below squeeze-risk levels."},
    {"label": "Volatility Stress", "value": 53, "note": "Implied volatility expanded without panic skew."},
    {"label": "Breakout Probability", "value": 79, "note": "Resistance break held through two retests."},
]


def _profile_for(ticker_value):
    return STOCK_PROFILES.get(ticker_value.upper(), DEFAULT_PROFILE)


def _dashboard_context(profile=None, active_page="dashboard"):
    profile = profile or DEFAULT_PROFILE
    return {
        "active_page": active_page,
        "profile": profile,
        "market_snapshot": MARKET_SNAPSHOT,
        "drivers": DRIVERS,
        "timeline": TIMELINE,
        "sentiment": SENTIMENT,
        "similar_events": SIMILAR_EVENTS,
        "intelligence_metrics": INTELLIGENCE_METRICS,
    }


def index(request):
    return render(request, "index.html", _dashboard_context(active_page="dashboard"))


def search(request):
    return render(request, "search.html", _dashboard_context(active_page="why_moved"))


def ticker(request):
    return render(
        request,
        "ticker.html",
        {
            **_dashboard_context(),
            "active_page": "markets",
            "ticker_list": MARKET_SNAPSHOT,
        },
    )


def predict(request, ticker_value, number_of_days):
    profile = _profile_for(ticker_value)
    return render(
        request,
        "result.html",
        {
            **_dashboard_context(profile),
            "active_page": "stocks",
            "ticker_value": profile["ticker"],
            "number_of_days": number_of_days,
        },
    )
