"""Server-owned output validators reused by published business templates."""


def final_report(value):
    text = value["final_output"].strip()
    if not text:
        raise ValueError("Final report must contain non-whitespace text")
    return {"final_output": text}
