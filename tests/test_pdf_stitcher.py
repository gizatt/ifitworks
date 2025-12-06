"""
Basic unit tests for pdf_stitcher module.
"""

import subprocess
import sys


def test_pdf_stitcher_import():
    """Test that pdf_stitcher module can be imported."""
    from ifitworks import pdf_stitcher
    assert hasattr(pdf_stitcher, "stitch_pattern_pdf")
    assert hasattr(pdf_stitcher, "main")


def test_stitch_pattern_pdf_function_exists():
    """Test that stitch_pattern_pdf function is accessible from package."""
    from ifitworks import stitch_pattern_pdf
    assert callable(stitch_pattern_pdf)


def test_pdf_stitcher_main_exists():
    """Test that main function is accessible from package."""
    from ifitworks import pdf_stitcher_main
    assert callable(pdf_stitcher_main)


def test_pdf_stitcher_cli_help():
    """Test that pdf-stitcher CLI can be run with --help."""
    result = subprocess.run(
        [sys.executable, "-m", "ifitworks.pdf_stitcher", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Stitch tiled PDF pages" in result.stdout
