"""Text overlap observations, never a contamination or literary verdict."""
import unicodedata

from ..candidate_reviews import digest
from ..evaluation.style_reference import HAN


def overlap_observations(candidate: str, reference: str, *, n: int = 8) -> dict:
    if type(n) is not int or not 1 <= n <= 64:
        raise ValueError("INVALID_OVERLAP_N")
    def grams(text):
        return [text[i:i+n] for i in range(max(0, len(text)-n+1))]
    def measured(left, right):
        windows, target = grams(left), set(grams(right))
        matched = sum(window in target for window in windows)
        return {"candidate_windows": len(windows), "matched_candidate_windows": matched,
                "fraction": matched / len(windows) if windows else None,
                "exact_candidate_substring_present": bool(left) and left in right}
    normalize = lambda text: "".join(HAN.findall(unicodedata.normalize("NFKC", text)))
    return {"status": "OBSERVED", "n": n, "candidate_sha256": digest(candidate.encode()),
            "reference_sha256": digest(reference.encode()), "character_count": len(candidate),
            "exact": measured(candidate, reference),
            "normalized_han": measured(normalize(candidate), normalize(reference)),
            "normalization": "NFKC_THEN_HAN_ONLY",
            "interpretation": "OVERLAP_OBSERVATION_NOT_PROOF_OF_MEMORIZATION_OR_CONTAMINATION",
            "model_pretraining_exposure": "UNKNOWN", "verdict": None, "authority_effect": "NONE"}
