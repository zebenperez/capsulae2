import os
import re
from dataclasses import dataclass

from django.conf import settings


SPANISH_TAX_ID_PATTERNS = (
    re.compile(r"^[0-9]{8}[A-Z]$"),
    re.compile(r"^[XYZ][0-9]{7}[A-Z]$"),
    re.compile(r"^[ABCDEFGHJNPQRSUVW][0-9]{7}[0-9A-J]$"),
)


def normalize_tax_id(value):
    if value is None:
        return ""
    normalized = re.sub(r"[^A-Z0-9]", "", str(value).strip().upper())
    if normalized.startswith("ES"):
        without_prefix = normalized[2:]
        if any(pattern.fullmatch(without_prefix) for pattern in SPANISH_TAX_ID_PATTERNS):
            normalized = without_prefix
    return normalized


def jaro_winkler_similarity(left, right):
    if left == right:
        return 1.0
    if not left or not right:
        return 0.0
    match_distance = max(len(left), len(right)) // 2 - 1
    match_distance = max(0, match_distance)
    left_matches = [False] * len(left)
    right_matches = [False] * len(right)
    matches = 0
    for left_index, char in enumerate(left):
        start = max(0, left_index - match_distance)
        end = min(left_index + match_distance + 1, len(right))
        for right_index in range(start, end):
            if right_matches[right_index] or char != right[right_index]:
                continue
            left_matches[left_index] = True
            right_matches[right_index] = True
            matches += 1
            break
    if not matches:
        return 0.0
    matched_left = [left[index] for index in range(len(left)) if left_matches[index]]
    matched_right = [right[index] for index in range(len(right)) if right_matches[index]]
    transpositions = sum(a != b for a, b in zip(matched_left, matched_right)) / 2.0
    jaro = (
        matches / len(left)
        + matches / len(right)
        + (matches - transpositions) / matches
    ) / 3.0
    prefix = 0
    for left_char, right_char in zip(left, right):
        if left_char != right_char or prefix == 4:
            break
        prefix += 1
    return jaro + prefix * 0.1 * (1.0 - jaro)


def damerau_levenshtein_distance(left, right):
    rows = len(left) + 1
    columns = len(right) + 1
    matrix = [[0] * columns for _ in range(rows)]
    for row in range(rows):
        matrix[row][0] = row
    for column in range(columns):
        matrix[0][column] = column
    for row in range(1, rows):
        for column in range(1, columns):
            substitution_cost = 0 if left[row - 1] == right[column - 1] else 1
            matrix[row][column] = min(
                matrix[row - 1][column] + 1,
                matrix[row][column - 1] + 1,
                matrix[row - 1][column - 1] + substitution_cost,
            )
            if (
                row > 1
                and column > 1
                and left[row - 1] == right[column - 2]
                and left[row - 2] == right[column - 1]
            ):
                matrix[row][column] = min(matrix[row][column], matrix[row - 2][column - 2] + 1)
    return matrix[-1][-1]


def get_supplier_similarity_threshold():
    configured = getattr(settings, "INVOICE_SUPPLIER_JARO_WINKLER_THRESHOLD", None) or os.getenv(
        "INVOICE_SUPPLIER_JARO_WINKLER_THRESHOLD", "0.90"
    )
    try:
        return float(configured)
    except (TypeError, ValueError):
        return 0.90


def get_supplier_max_distance():
    configured = getattr(settings, "INVOICE_SUPPLIER_MAX_DAMERAU_DISTANCE", None) or os.getenv(
        "INVOICE_SUPPLIER_MAX_DAMERAU_DISTANCE", "1"
    )
    try:
        return max(0, int(configured))
    except (TypeError, ValueError):
        return 1


def get_supplier_suggestion_limit():
    configured = getattr(settings, "INVOICE_SUPPLIER_SUGGESTION_LIMIT", None) or os.getenv(
        "INVOICE_SUPPLIER_SUGGESTION_LIMIT", "5"
    )
    try:
        return max(1, int(configured))
    except (TypeError, ValueError):
        return 5


@dataclass(frozen=True)
class SupplierCandidate:
    id: int
    name: str
    nif: str
    normalized_nif: str
    distance: int
    similarity: float


@dataclass(frozen=True)
class SupplierMatchResult:
    original_tax_id: str
    normalized_tax_id: str
    exact_matches: tuple
    suggestions: tuple

    @property
    def unique_exact(self):
        return self.exact_matches[0] if len(self.exact_matches) == 1 else None


def match_suppliers(extracted_tax_id, suppliers):
    original = "" if extracted_tax_id is None else str(extracted_tax_id).strip()
    normalized = normalize_tax_id(original)
    if not normalized:
        return SupplierMatchResult(original, normalized, (), ())

    rows = []
    for supplier in suppliers.values("id", "name", "nif"):
        registered = normalize_tax_id(supplier["nif"])
        rows.append((supplier, registered))
    exact = sorted((
        SupplierCandidate(row["id"], row["name"], row["nif"], registered, 0, 1.0)
        for row, registered in rows
        if registered == normalized
    ), key=lambda item: (item.name.casefold(), item.id))
    if exact:
        return SupplierMatchResult(original, normalized, tuple(exact), ())

    threshold = get_supplier_similarity_threshold()
    max_distance = get_supplier_max_distance()
    suggestions = []
    for row, registered in rows:
        if not registered:
            continue
        distance = damerau_levenshtein_distance(normalized, registered)
        if distance > max_distance:
            continue
        similarity = jaro_winkler_similarity(normalized, registered)
        if similarity < threshold:
            continue
        suggestions.append(SupplierCandidate(
            row["id"], row["name"], row["nif"], registered, distance, similarity
        ))
    suggestions.sort(key=lambda item: (item.distance, -item.similarity, item.name.casefold(), item.id))
    return SupplierMatchResult(original, normalized, (), tuple(suggestions[:get_supplier_suggestion_limit()]))
