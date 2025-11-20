"""Add AI Governance origins to the database"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import ScrapingOrigin, SessionLocal, init_db
from app.core.scheduler import schedule_origin

# Define all AI governance origins
ORIGINS = [
    # United States
    {
        "name": "United States - White House AI Executive Order 2025",
        "url": "https://www.whitehouse.gov/presidential-actions/2025/01/removing-barriers-to-american-leadership-in-artificial-intelligence/"
    },
    {
        "name": "United States - Federal Register AI Safety Order 2023",
        "url": "https://www.federalregister.gov/documents/2023/11/01/2023-24283/safe-secure-and-trustworthy-development-and-use-of-artificial-intelligence"
    },
    # Canada
    {
        "name": "Canada - Artificial Intelligence and Data Act",
        "url": "https://ised-isde.canada.ca/site/innovation-better-canada/en/artificial-intelligence-and-data-act"
    },
    # Brazil
    {
        "name": "Brazil - Brazilian AI Strategy",
        "url": "https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/estrategias-e-politicas-digitais/estrategia-brasileira-de-inteligencia-artificial"
    },
    # United Kingdom
    {
        "name": "United Kingdom - National AI Strategy",
        "url": "https://assets.publishing.service.gov.uk/media/614db4d1e90e077a2cbdf3c4/National_AI_Strategy_-_PDF_version.pdf"
    },
    # European Union
    {
        "name": "European Union - AI Act 2024",
        "url": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng"
    },
    # France
    {
        "name": "France - National AI Research Program",
        "url": "https://www.inria.fr/sites/default/files/2021-06/PNRIA-Flyer_National_EN.pdf"
    },
    # Germany
    {
        "name": "Germany - AI Strategy",
        "url": "https://www.ki-strategie-deutschland.de/"
    },
    # India
    {
        "name": "India - National Strategy for Artificial Intelligence",
        "url": "https://www.niti.gov.in/sites/default/files/2023-03/National-Strategy-for-Artificial-Intelligence.pdf"
    },
    # China
    {
        "name": "China - AI Development Plan 2017 (Original)",
        "url": "https://www.gov.cn/zhengce/content/2017-07/20/content_5211996.htm"
    },
    {
        "name": "China - AI Development Plan 2017 (English Translation)",
        "url": "https://digichina.stanford.edu/work/full-translation-chinas-new-generation-artificial-intelligence-development-plan-2017/"
    },
    # Japan
    {
        "name": "Japan - AI Strategy 2019",
        "url": "https://www8.cao.go.jp/cstp/ai/aistratagy2019en.pdf"
    },
    # South Korea
    {
        "name": "South Korea - AI Strategy",
        "url": "https://www.msit.go.kr/bbs/view.do?bbsSeqNo=46&mId=10&mPid=9&nttSeqNo=9&sCode=eng"
    },
    # Singapore
    {
        "name": "Singapore - National AI Strategy",
        "url": "https://www.smartnation.gov.sg/initiatives/national-ai-strategy/"
    },
    # Australia
    {
        "name": "Australia - AI Strategy",
        "url": "https://www.industry.gov.au/science-technology-and-innovation/technology/artificial-intelligence"
    },
    # United Arab Emirates
    {
        "name": "United Arab Emirates - National AI Strategy 2031",
        "url": "https://staticcdn.mbzuai.ac.ae/mbzuaiwpprd01/2022/07/UAE-National-Strategy-for-Artificial-Intelligence-2031.pdf"
    },
    # Kenya
    {
        "name": "Kenya - AI Strategy 2025-2030",
        "url": "https://ict.go.ke/sites/default/files/2025-03/Kenya%20AI%20Strategy%202025%20-%202030.pdf"
    },
    # South Africa
    {
        "name": "South Africa - National AI Policy Framework",
        "url": "https://www.dcdt.gov.za/sa-national-ai-policy-framework/file/338-sa-national-ai-policy-framework.html"
    },
]

def add_origins():
    """Add all AI governance origins to the database"""
    print("Initializing database...")
    init_db()
    
    db = SessionLocal()
    try:
        added_count = 0
        skipped_count = 0
        error_count = 0
        
        print(f"\nAdding {len(ORIGINS)} AI governance origins...")
        print("=" * 60)
        
        for origin_data in ORIGINS:
            name = origin_data["name"]
            url = origin_data["url"]
            
            try:
                # Check if origin with this URL already exists
                existing = db.query(ScrapingOrigin).filter(ScrapingOrigin.url == url).first()
                
                if existing:
                    print(f"[SKIP] Already exists: {name}")
                    skipped_count += 1
                    continue
                
                # Create new origin
                origin = ScrapingOrigin(
                    name=name,
                    url=url,
                    frequency_hours=24,
                    enabled=True
                )
                
                db.add(origin)
                db.commit()
                db.refresh(origin)
                
                # Schedule the origin for crawling
                try:
                    schedule_origin(origin)
                    scheduled = True
                except Exception as schedule_error:
                    scheduled = False
                    schedule_msg = f" (scheduling failed: {schedule_error})"
                
                print(f"[OK] Added: {name}")
                print(f"      URL: {url}")
                print(f"      ID: {origin.id}")
                if scheduled:
                    print(f"      Scheduled for 24-hour crawling")
                else:
                    print(f"      Warning: Could not schedule (will be scheduled on server restart)")
                added_count += 1
                
            except Exception as e:
                print(f"[ERROR] Failed to add {name}: {e}")
                db.rollback()
                error_count += 1
        
        print("=" * 60)
        print(f"\nSummary:")
        print(f"  Added: {added_count}")
        print(f"  Skipped (already exists): {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total: {len(ORIGINS)}")
        
        if added_count > 0:
            print(f"\n[OK] Successfully added {added_count} new origins!")
            print("Origins are set to crawl every 24 hours and are enabled by default.")
        
    except Exception as e:
        print(f"Error adding origins: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_origins()

