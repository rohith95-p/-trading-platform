import asyncio
from src.database import SessionLocal
from src.services.background_tasks import start_news_ingestion_loop
import logging

# Silence noisy loggers
logging.basicConfig(level=logging.INFO)

async def trigger_once():
    print("Triggering manual ingestion cycle...")
    db = SessionLocal()
    from src.intelligence.news.news_stream import NewsStreamService
    from src.api.intelligence import get_classifier
    
    stream_service = NewsStreamService(db)
    stats = await stream_service.run_ingestion_cycle()
    print(f"Ingested: {stats}")
    
    # Fetch articles to classify (either newly ingested or last 10)
    from src.data.models import NewsArticle as NewsArticleDB
    from sqlalchemy import select
    
    limit = stats["total"] if stats["total"] > 0 else 1
    query = select(NewsArticleDB).order_by(NewsArticleDB.created_at.desc()).limit(1)
    articles = db.execute(query).scalars().all()
    
    if articles:
        print(f"Processing {len(articles)} articles...")
        classifier = get_classifier()
        for article in articles:
            print(f"Classifying: {article.title[:50]}...")
            payload = {
                "title": article.title,
                "content": article.content,
                "source": article.source,
                "url": article.url,
                "user_id": "system" 
            }
            result = await classifier.classify(payload)
            if result.get("signals"):
                from src.data.models import Signal as SignalDB
                from src.core.time import utc_now
                for signal_data in result["signals"]:
                    signal = SignalDB(
                        user_id="system",
                        source="news_classification",
                        asset=signal_data["asset"],
                        direction=signal_data["direction"],
                        confidence=signal_data["confidence"],
                        rationale=signal_data["rationale"],
                        indicators={"article_url": article.url},
                        timestamp=utc_now(),
                    )
                    db.add(signal)
                db.commit()
                print(f"  Generated {len(result['signals'])} signals")
    db.close()

if __name__ == "__main__":
    asyncio.run(trigger_once())
