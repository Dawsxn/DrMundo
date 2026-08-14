"""Tests for redaction, triage and the reader interface (Phase 5). No API calls."""

from pathlib import Path

import pytest
from PIL import Image

from vision.extract_request import extract_request, triage
from vision.reader import OracleReader, ReadMark, ReadResult
from vision.redact import load_and_redact, redact_regions
from eval.reader_bench import dataset_dir


def _img(w: int = 200, h: int = 100) -> Image.Image:
    return Image.new("RGB", (w, h), "white")


# ------------------------------------------------------------------ redaction
def test_redaction_destroys_pixels_not_metadata():
    img = _img()
    out = redact_regions(img, [(0, 0, 50, 50)], labels=["PATIENT_NAME"])
    assert out.image.getpixel((10, 10)) == (0, 0, 0)      # actually painted
    assert out.redacted is True
    assert out.labels == ["PATIENT_NAME"]


def test_redaction_leaves_the_caller_original_untouched():
    img = _img()
    redact_regions(img, [(0, 0, 50, 50)])
    assert img.getpixel((10, 10)) == (255, 255, 255)


def test_redaction_hash_changes_with_content():
    img = _img()
    a = redact_regions(img, [(0, 0, 10, 10)])
    b = redact_regions(img, [(0, 0, 90, 90)])
    assert a.sha256 != b.sha256


def test_synthetic_images_are_not_claimed_as_redacted(tmp_path):
    p = tmp_path / "x.png"
    _img().save(p)
    out = load_and_redact(p, synthetic=True)
    assert out.labels == []
    assert out.redacted is False        # nothing was covered, and we do not pretend


def test_unknown_layout_defaults_to_covering_a_band(tmp_path):
    p = tmp_path / "x.png"
    _img().save(p)
    out = load_and_redact(p)
    assert out.redacted is True
    assert "PATIENT_NAME" in out.labels


# ------------------------------------------------------------------ triage policy
def _read(*marks: ReadMark) -> ReadResult:
    return ReadResult(marks=list(marks), reader="test")


def test_resolved_confident_items_are_priceable():
    slip = extract_request(_read(ReadMark(label="CBC")), "h", synthetic=True)
    assert triage(slip)["priceable"][0].test_code == "CBC"


def test_ambiguous_label_goes_to_confirmation_not_to_a_price():
    # "PT" is prothrombin time OR pregnancy test.
    slip = extract_request(_read(ReadMark(label="PT")), "h", synthetic=True)
    t = triage(slip)
    assert t["priceable"] == []
    assert len(t["needs_confirmation"]) == 1


def test_section_heading_rescues_an_ambiguous_label():
    slip = extract_request(
        _read(ReadMark(label="KUB", section="Ultrasound")), "h", synthetic=True
    )
    assert triage(slip)["priceable"][0].test_code == "US_KUB"


def test_unresolved_label_is_asked_about_not_dropped():
    slip = extract_request(_read(ReadMark(label="zzz unknown")), "h", synthetic=True)
    t = triage(slip)
    assert len(t["needs_confirmation"]) == 1
    assert t["priceable"] == []


def test_low_confidence_read_routes_to_confirmation():
    slip = extract_request(
        _read(ReadMark(label="CBC", confidence=0.2)), "h", synthetic=True
    )
    assert triage(slip)["needs_confirmation"]


def test_cancelled_marks_never_reach_priceable():
    slip = extract_request(
        _read(ReadMark(label="CBC"), ReadMark(label="FBS", cancelled=True)),
        "h", synthetic=True,
    )
    t = triage(slip)
    assert [i.test_code for i in t["priceable"]] == ["CBC"]
    assert [i.raw_text for i in t["cancelled"]] == ["FBS"]


def test_every_item_lands_in_exactly_one_bucket():
    slip = extract_request(
        _read(
            ReadMark(label="CBC"),
            ReadMark(label="PT"),
            ReadMark(label="FBS", cancelled=True),
            ReadMark(label="zzz"),
        ),
        "h", synthetic=True,
    )
    t = triage(slip)
    assert len(t["priceable"]) + len(t["needs_confirmation"]) + len(t["cancelled"]) == 4


def test_non_request_document_is_flagged():
    read = ReadResult(marks=[], is_laboratory_request=False, reader="test")
    slip = extract_request(read, "h", synthetic=True)
    assert slip.is_laboratory_request is False


# ------------------------------------------------------------------ oracle reader
def test_oracle_reader_reproduces_ground_truth():
    base = dataset_dir()
    reader = OracleReader(base / "groundtruth")
    res = reader.read(base / "media" / "0000000_clean.png")
    assert res.ok
    assert len(res.marks) > 0
    assert res.reader == "oracle"


def test_oracle_reader_reports_a_missing_sample_rather_than_raising():
    reader = OracleReader(dataset_dir() / "groundtruth")
    res = reader.read(Path("9999999_clean.png"))
    assert res.ok is False
    assert "no ground truth" in res.error
