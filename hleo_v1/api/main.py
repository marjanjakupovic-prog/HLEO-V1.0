from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from core.database import SessionLocal
from core.models import ClinicalProfile
from collectors.reddit import RedditCollector
from pydantic import BaseModel
from crawlers.crawler import ThreadCrawler
from search.manager import SearchManager
from core.parser import ClinicalParser
from core.extractor import LLMExtractor

app = FastAPI()
class ThreadRequest(BaseModel):
    url: str

search_manager = SearchManager()
parser = ClinicalParser()
extractor = LLMExtractor()

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>HLEO - Ricerca Profili Clinici</title>
</head>
<body style="font-family:Arial;background:#f3f4f6;">
    <div style="max-width:500px;margin:60px auto;padding:20px;background:white;border-radius:10px;">
        <h2>HLEO - Ricerca Profili Clinici</h2>

        <form action="/analizza" method="post">
            <textarea
                name="testo"
                placeholder="Inserisci il nome da cercare"
                rows="8"
                style="width:100%;"></textarea>

            <br><br>

            <button
                type="submit"
                style="width:100%;padding:10px;">
                Analizza
            </button>
        </form>
    </div>
</body>
</html>"""

@app.post("/analizza", response_class=HTMLResponse)
async def analizza_testo(testo: str = Form(...)):
    db = SessionLocal()

    try:
        query = select(ClinicalProfile)
        risultati = db.execute(query).scalars().all()

        html = """
        <!DOCTYPE html>
        <html lang="it">
        <head>
            <meta charset="UTF-8">
            <title>Risultati HLEO</title>
        </head>
        <body style="font-family:Arial;background:#f3f4f6;">
            <div style="max-width:700px;margin:60px auto;padding:20px;background:white;border-radius:10px;">
                <h2>Risultati</h2>
                <p><b>Testo inserito:</b> """ + testo + """</p>
                <ul>
        """

        if risultati:
            for p in risultati:
                html += (
                    f"<li>"
                    f"ID: {p.id} | "
                    f"Episode: {p.episode_id} | "
                    f"Categoria: {p.final_category} | "
                    f"Confidenza: {p.confidence_score}"
                    f"</li>"
                )
        else:
            html += "<li>Nessun record trovato.</li>"

        html += """
                </ul>

                <br>

                <a href="/">← Torna alla ricerca</a>

            </div>
        </body>
        </html>
        """

        return HTMLResponse(content=html)

    finally:
        db.close()

@app.get("/health")
def health():
    collector = RedditCollector()

    risultati = collector.search("dutasteride", limit=3)

    return {
        "status": "ok",
        "reddit_posts": len(risultati)
    }
    from pydantic import BaseModel


class ThreadRequest(BaseModel):
    url: str
    
@app.post("/crawl-thread")
def crawl_thread(request: ThreadRequest):

    urls = search_manager.search(request.url)

    crawler = ThreadCrawler()

    results = []

    for url in urls:

        html = crawler.fetch(url)

        if html:

            text = crawler.extract_text(html)
            parsed = extractor.extract(text)

        else:

            text = ""
            parsed = {}
        results.append({
            "url": url,
            "status": "ok" if html else "failed",
            "characters": len(text),
            "preview": text[:500],
            "clinical_data": parsed
        })

    return {
        "query": request.url,
        "results": results,
        "count": len(results)
    }