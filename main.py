from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import json

import httpx
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Load store -> API key mapping
with open("stores.json") as f:
    STORE_KEYS = json.load(f)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


async def get_wsr_report(store_api_key: str):
    """
    Fetch WSR counts for current month + previous 5 months.
    """

    now = datetime.now(timezone.utc)

    current_month_start = now.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    start_month = current_month_start - relativedelta(months=5)

    payload = {
        "data": {
            "type": "metric-aggregate",
            "attributes": {
                "metric_id": "WzJW4j",
                "measurements": ["count"],
                "interval": "month",
                "timezone": "UTC",
                "filter": [
                    f"greater-or-equal(datetime,{start_month.strftime('%Y-%m-%dT%H:%M:%S')})",
                    f"less-than(datetime,{now.strftime('%Y-%m-%dT%H:%M:%S')})",
                ],
            },
        }
    }

    headers = {
        "Authorization": f"Klaviyo-API-Key {store_api_key}",
        "accept": "application/vnd.api+json",
        "content-type": "application/vnd.api+json",
        "revision": "2026-04-15",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://a.klaviyo.com/api/metric-aggregates",
            headers=headers,
            json=payload,
        )

    response.raise_for_status()

    response_data = response.json()

    attributes = response_data.get("data", {}).get("attributes", {})

    dates = attributes.get("dates", [])

    count_values = (
        attributes.get("data", [{}])[0]
        .get("measurements", {})
        .get("count", [])
    )

    report = []

    for date, count in zip(dates, count_values):
        report.append(
            {
                "month": date[:7],
                "count": int(count) if count is not None else 0,
            }
        )

    return report


@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "stores": list(STORE_KEYS.keys()),
        },
    )


@app.post("/fetch-report")
async def fetch_report(
    request: Request,
    store: str = Form(...)
):
    api_key = STORE_KEYS.get(store)

    if not api_key:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "stores": list(STORE_KEYS.keys()),
                "error": "Invalid store selected.",
            },
        )

    try:
        report = await get_wsr_report(api_key)

        total_count = sum(item["count"] for item in report)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "stores": list(STORE_KEYS.keys()),
                "store": store,
                "report": report,
                "total_count": total_count,
            },
        )

    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "stores": list(STORE_KEYS.keys()),
                "error": str(e),
            },
        )