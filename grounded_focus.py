"""Only publish an AI-selected, complete original sentence, never a prediction."""
import re


def validate_focus(point, evidence, title, description):
    point, evidence = (point or '').strip(), (evidence or '').strip()
    if not 12 <= len(point) <= 120 or point != evidence:
        return None
    sentences = [s.strip() for s in re.split(r'(?<=。)', description or '') if s.strip().endswith('。')]
    if point not in sentences:  # Do not truncate qualifications or use headline-only inference.
        return None
    return dict(point=point, evidence=evidence)
