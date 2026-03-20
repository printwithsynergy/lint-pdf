"""Tests for Part 3 interpreter additions — HT/TR/BG/UCR detection, OPI/alternate."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.semantic.events import ImagePlacedEvent, PrepressStateChangedEvent
from grounded.semantic.interpreter import ContentStreamInterpreter


def _make_resources(**kwargs: object) -> dict[str, object]:
    """Build a minimal resources dict."""
    return dict(kwargs)


class TestPrepressDetection:
    """Test halftone, transfer function, BG/UCR detection in _handle_gs."""

    def test_halftone_detected(self) -> None:
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

    def test_transfer_function_detected(self) -> None:
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

    def test_transfer_function_tr2_detected(self) -> None:
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

    def test_transfer_identity_not_detected(self) -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/TR": "/Identity"},
            },
        }
        interp = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interp.interpret([(["/GS1"], "gs")])
        prepress = [e for e in events if isinstance(e, PrepressStateChangedEvent)]
        assert len(prepress) == 0

    def test_bg_detected(self) -> None:
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

    def test_ucr2_detected(self) -> None:
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

    def test_no_prepress_no_event(self) -> None:
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

    def test_combined_prepress(self) -> None:
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

    def test_opi_detected(self) -> None:
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

    def test_alternate_detected(self) -> None:
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

    def test_no_opi_no_alternate(self) -> None:
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
