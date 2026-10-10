import logging

from fastapi import APIRouter, Depends, HTTPException
from google.genai.errors import APIError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.rag.citation_validator import validate_answer_citations
from app.rag.generation_service import (
    LANGUAGE_NAMES,
    generate_grounded_answer,
)
from app.rag.hybrid_retriever import retrieve_hybrid
from app.schemas.chat import AskRequest

router = APIRouter()
logger = logging.getLogger(__name__)


NO_EVIDENCE_MESSAGES = {
    "en": "I couldn't find sufficient supporting passages in the current corpus.",
    "hi": "वर्तमान स्रोत-संग्रह में इस प्रश्न के लिए पर्याप्त प्रमाण नहीं मिले।",
    "mr": "सध्याच्या स्रोत-संग्रहात या प्रश्नासाठी पुरेसे पुरावे सापडले नाहीत.",
    "sd": "موجوده معلوماتي ذخيري ۾ هن سوال جو جواب ڏيڻ لاءِ ڪافي مستند حوالا نه مليا.",
    "sd-Arab": "موجوده معلوماتي ذخيري ۾ هن سوال جو جواب ڏيڻ لاءِ ڪافي مستند حوالا نه مليا.",
    "sd-Deva": "موجوده معلوماتी ذخيري में इस सवाल के लिए पर्याप्त प्रमाण नहीं मिले।",
}


@router.post("/ask")
def ask(
    request: AskRequest,
    db: Session = Depends(get_db),
):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question cannot be empty.",
        )

    try:
        retrieved = retrieve_hybrid(
            db=db,
            query=question,
            language=request.source_language,
            limit=request.limit,
        )
    except Exception:
        logger.exception("Shlokantara retrieval failed")
        raise HTTPException(
            status_code=500,
            detail="Retrieval failed. Check the backend logs.",
        )

    if not retrieved:
        return {
            "answer": NO_EVIDENCE_MESSAGES.get(
                request.answer_language,
                NO_EVIDENCE_MESSAGES["en"],
            ),
            "answer_language": request.answer_language,
            "answer_language_name": LANGUAGE_NAMES.get(
                request.answer_language,
                request.answer_language,
            ),
            "evidence": [],
            "citations": [],
            "grounded": False,
        }

    evidence = []

    for index, item in enumerate(retrieved, start=1):
        evidence.append({
            "citation_id": f"S{index}",
            "verse_id": item["verse_id"],
            "chapter_number": item["chapter_number"],
            "verse_number": item["verse_number"],
            "content_type": item["content_type"],
            "language_code": item["language_code"],
            "content": item["content"],
            "source": item["source"],
        })

    try:
        answer = generate_grounded_answer(
            question=question,
            answer_language=request.answer_language,
            evidence=evidence,
        )
    except APIError:
        logger.exception("Gemini API request failed")
        raise HTTPException(
            status_code=502,
            detail="Gemini generation failed. Check the model and API key.",
        )
    except RuntimeError as exc:
        logger.exception("Gemini configuration or generation error")
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )
    except Exception:
        logger.exception("Unexpected answer-generation failure")
        raise HTTPException(
            status_code=502,
            detail="Answer generation failed. Check the backend logs.",
        )

    answer, valid_citations = validate_answer_citations(
        answer,
        evidence,
    )

    grounded = bool(valid_citations)

    if not grounded:
        answer = {
            "en": "Relevant passages were retrieved, but the generated answer did not contain verifiable citations. Please inspect the evidence below.",
            "hi": "संबंधित अंश मिले, लेकिन उत्तर के उद्धरण सत्यापित नहीं हो सके। कृपया नीचे दिए गए स्रोत देखें।",
            "mr": "संबंधित उतारे सापडले, पण उत्तरातील संदर्भ पडताळता आले नाहीत. कृपया खालील पुरावे तपासा.",
            "sd": "لاڳاپيل حوالا مليا، پر جواب ۾ ڏنل حوالن جي تصديق نه ٿي سگهي. مهرباني ڪري هيٺ ڏنل مواد ڏسو.",
            "sd-Arab": "لاڳاپيل حوالا مليا، پر جواب ۾ ڏنل حوالن جي تصديق نه ٿي سگهي. مهرباني ڪري هيٺ ڏنل مواد ڏسو.",
        }.get(
            request.answer_language,
            "Relevant passages were retrieved, but the answer could not be citation-verified. Please inspect the evidence below.",
        )

    citation_lookup = {
        item["citation_id"]: item
        for item in evidence
    }

    return {
        "answer": answer,
        "answer_language": request.answer_language,
        "answer_language_name": LANGUAGE_NAMES.get(
            request.answer_language,
            request.answer_language,
        ),
        "evidence": evidence,
        "citations": [
            citation_lookup[citation_id]
            for citation_id in valid_citations
        ],
        "grounded": grounded,
    }
