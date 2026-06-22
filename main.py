from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import os

import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI()

KLAVIYO_URL = "https://a.klaviyo.com/api/metric-aggregates"
KLAVIYO_REVISION = "2026-04-15"


@app.get("/metric-months")
async def get_metric_months():
    api_key = os.getenv("KLAVIYO_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="KLAVIYO_API_KEY is not set"
        )

    now = datetime.now(timezone.utc)

    # Current month start (UTC)
    current_month_start = now.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    # Include current month + previous 5 months
    start_month = current_month_start - relativedelta(months=5)

    start_filter = start_month.strftime("%Y-%m-%dT%H:%M:%S")
    end_filter = now.strftime("%Y-%m-%dT%H:%M:%S")

    payload = {
        "data": {
            "type": "metric-aggregate",
            "attributes": {
                "metric_id": "WzJW4j",
                "measurements": ["count"],
                "interval": "month",
                "timezone": "UTC",
                "filter": [
                    f"greater-or-equal(datetime,{start_filter})",
                    f"less-than(datetime,{end_filter})",
                ],
            },
        }
    }

    headers = {
        "Authorization": f"Klaviyo-API-Key {api_key}",
        "accept": "application/vnd.api+json",
        "content-type": "application/vnd.api+json",
        "revision": KLAVIYO_REVISION,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            KLAVIYO_URL,
            headers=headers,
            json=payload,
        )

    if response.is_error:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    response_data = response.json()
    print(response_data)
    
    attributes = response_data.get("data", {}).get("attributes", {})
    dates = attributes.get("dates", [])

    count_values = (
        attributes.get("data", [{}])[0]
        .get("measurements", {})
        .get("count", [])
    )

    return [
        {
            "month": date[:7],  # YYYY-MM
            "count": int(count) if count is not None else 0,
        }
        for date, count in zip(dates, count_values)
    ]

{'data': {'type': 'metric-aggregate', 'id': '8679205039878477414', 'attributes': {'dates': ['2026-01-01T00:00:00+00:00', '2026-02-01T00:00:00+00:00', '2026-03-01T00:00:00+00:00', '2026-04-01T00:00:00+00:00', '2026-05-01T00:00:00+00:00', '2026-06-01T00:00:00+00:00'], 'data': [{'dimensions': [], 'measurements': {'count': [41637.0, 3237.0, 1749.0, 1525.0, 910.0, 431.0]}}]}, 'links': {'self': 'https://a.klaviyo.com/api/metric-aggregates/'}}, 'links': {'self': 'https://a.klaviyo.com/api/metric-aggregates', 'next': None, 'prev': None}}
