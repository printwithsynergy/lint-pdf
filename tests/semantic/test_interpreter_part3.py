"""Tests for Part 3 interpreter additions — HT/TR/BG/UCR detection, OPI/alternate."""

from __future__ import annotations

from siftpdf.semantic.events import ImagePlacedEvent, PrepressStateChangedEvent
from siftpdf.semantic.interpreter import ContentStreamInterpreter


def _make_resources(**kwargs: object) -> dict[str, object]:
    """Build a minimal resources dict."""
    return dict(kwargs)


class TestPrepressDetection:
    """Test halftone, transfer function, BG/UCR detection in _handle_gs."""

    @staticmethod
    def test_halftone_detected() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/HT": {"/Type": "/Halftone", "/HalftoneType": 1}},
            },
        }
        interp = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interp.interpret([(["/GS1"], "gs")])
        prepress = [e for e in events if isinstance(e, PrepressStateChangedEvent)]
        assert len(prepress) == 1
        assert prepress[0].has_halftone is True

    @staticmethod
    def test_transfer_function_detected() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/TR": {"/FunctionType": 0}},
            },
        }
        interp = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interp.interpret([(["/GS1"], "gs")])
        prepress = [e for e in events if isinstance(e, PrepressStateChangedEvent)]
        assert len(prepress) == 1
        assert prepress[0].has_transfer_function is True

    @staticmethod
    def test_transfer_function_tr2_detected() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/TR2": {"/FunctionType": 0}},
            },
        }
        interp = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interp.interpret([(["/GS1"], "gs")])
        prepress = [e for e in events if isinstance(e, PrepressStateChangedEvent)]
        assert len(prepress) == 1
        assert prepress[0].has_transfer_function is True

    @staticmethod
    def test_transfer_identity_not_detected() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/TR": "/Identity"},
            },
        }
        interp = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interp.interpret([(["/GS1"], "gs")])
        prepress = [e for e in events if isinstance(e, PrepressStateChangedEvent)]
        assert len(prepress) == 0

    @staticmethod
    def test_bg_detected() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/BG": {"/FunctionType": 0}},
            },
        }
        interp = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interp.interpret([(["/GS1"], "gs")])
        prepress = [e for e in events if isinstance(e, PrepressStateChangedEvent)]
        assert len(prepress) == 1
        assert prepress[0].has_bg_ucr is True

    @staticmethod
    def test_ucr2_detected() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/UCR2": {"/FunctionType": 0}},
            },
        }
        interp = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interp.interpret([(["/GS1"], "gs")])
        prepress = [e for e in events if isinstance(e, PrepressStateChangedEvent)]
        assert len(prepress) == 1
        assert prepress[0].has_bg_ucr is True

    @staticmethod
    def test_no_prepress_no_event() -> None:
        """ExtGState with only opacity should not emit PrepressStateChangedEvent."""
        resources = {
            "/ExtGState": {
                "/GS1": {"/ca": 0.5},
            },
        }
        interp = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interp.interpret([(["/GS1"], "gs")])
        prepress = [e for e in events if isinstance(e, PrepressStateChangedEvent)]
        assert len(prepress) == 0

    @staticmethod
    def test_combined_prepress() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {
                    "/HT": {"/Type": "/Halftone"},
                    "/TR": {"/FunctionType": 0},
                    "/BG": {"/FunctionType": 0},
                },
            },
        }
        interp = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interp.interpret([(["/GS1"], "gs")])
        prepress = [e for e in events if isinstance(e, PrepressStateChangedEvent)]
        assert len(prepress) == 1
        assert prepress[0].has_halftone is True
        assert prepress[0].has_transfer_function is True
        assert prepress[0].has_bg_ucr is True


class TestOPIAlternateDetection:
    """Test OPI and alternate image detection in _handle_image_xobject."""

    @staticmethod
    def test_opi_detected() -> None:
        resources = {
            "/XObject": {
                "/Im1": {
                    "/Subtype": "/Image",
                    "/Width": 100,
                    "/Height": 100,
                    "/BitsPerComponent": 8,
                    "/ColorSpace": "/DeviceCMYK",
                    "/OPI": {"/Type": "/OPI", "/Version": 1.3},
                },
            },
        }
        interp = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interp.interpret([(["/Im1"], "Do")])
        images = [e for e in events if isinstance(e, ImagePlacedEvent)]
        assert len(images) == 1
        assert images[0].has_opi is True
        assert images[0].has_alternate is False

    @staticmethod
    def test_alternate_detected() -> None:
        resources = {
            "/XObject": {
                "/Im1": {
                    "/Subtype": "/Image",
                    "/Width": 100,
                    "/Height": 100,
                    "/BitsPerComponent": 8,
                    "/ColorSpace": "/DeviceCMYK",
                    "/Alternates": [{"something": "here"}],
                },
            },
        }
        interp = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interp.interpret([(["/Im1"], "Do")])
        images = [e for e in events if isinstance(e, ImagePlacedEvent)]
        assert len(images) == 1
        assert images[0].has_alternate is True
        assert images[0].has_opi is False

    @staticmethod
    def test_no_opi_no_alternate() -> None:
        resources = {
            "/XObject": {
                "/Im1": {
                    "/Subtype": "/Image",
                    "/Width": 100,
                    "/Height": 100,
                    "/BitsPerComponent": 8,
                    "/ColorSpace": "/DeviceCMYK",
                },
            },
        }
        interp = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interp.interpret([(["/Im1"], "Do")])
        images = [e for e in events if isinstance(e, ImagePlacedEvent)]
        assert len(images) == 1
        assert images[0].has_opi is False
        assert images[0].has_alternate is False
