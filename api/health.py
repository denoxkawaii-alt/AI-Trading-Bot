from datetime import datetime, timezone

def handler(request):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {
            "service": "AI-Trading-Bot",
            "status": "online",
            "mode": "paper-trading",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
