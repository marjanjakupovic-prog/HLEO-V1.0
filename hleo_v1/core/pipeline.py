def analyze_testimonial(text: str):
        return {
                "status": "ok",
                "length": len(text),
                "preview": text[:200]
         }