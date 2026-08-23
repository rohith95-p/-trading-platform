from src.database import SessionLocal
from src.data.models import Signal, NewsArticle
from sqlalchemy import select, func

def check_data():
    db = SessionLocal()
    try:
        # Check Signals
        signal_count = db.execute(select(func.count(Signal.id))).scalar()
        print(f"Total Signals in DB: {signal_count}")
        
        # Check Articles
        article_count = db.execute(select(func.count(NewsArticle.id))).scalar()
        print(f"Total News Articles in DB: {article_count}")
        
        # Show last 5 signals
        if signal_count > 0:
            print("\nLatest 5 Signals:")
            signals = db.execute(select(Signal).order_by(Signal.timestamp.desc()).limit(5)).scalars().all()
            for s in signals:
                print(f"- {s.timestamp}: {s.asset} {s.direction} (Confidence: {s.confidence})")
        
        # Show last 5 articles
        if article_count > 0:
            print("\nLatest 5 Articles:")
            articles = db.execute(select(NewsArticle).order_by(NewsArticle.created_at.desc()).limit(5)).scalars().all()
            for a in articles:
                print(f"- {a.created_at}: {a.title[:50]}... ({a.source})")
                
    finally:
        db.close()

if __name__ == "__main__":
    check_data()
