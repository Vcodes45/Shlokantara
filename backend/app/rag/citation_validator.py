import re


CITATION_PATTERN = re.compile(r"\[(S\d+)\]")


def validate_answer_citations(
    answer: str,
    evidence: list[dict],
) -> tuple[str, list[str]]:
    available = {
        item["citation_id"]
        for item in evidence
        if item.get("citation_id")
    }

    mentioned = list(dict.fromkeys(
        CITATION_PATTERN.findall(answer)
    ))

    valid_citations = [
        citation_id
        for citation_id in mentioned
        if citation_id in available
    ]

    def remove_invalid_citation(match):
        citation_id = match.group(1)

        if citation_id in available:
            return match.group(0)

        return ""

    cleaned_answer = CITATION_PATTERN.sub(
        remove_invalid_citation,
        answer,
    ).strip()

    if not valid_citations:
        return (
            "Unable to provide an answer with a verified citation. "
            "Please inspect the retrieved evidence.",
            [],
        )

    return cleaned_answer, valid_citations
