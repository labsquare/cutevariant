from cutevariant.gui.model_view import *

import filecmp
import tempfile


def test_pedmodel(qtmodeltester):
    """Test import/export of PED file into/from a pedigree model"""
    model = PedModel()

    pedfile = "examples/test.snpeff.pedigree.tfam"

    assert model.rowCount() == 0

    # Test import
    model.from_pedfile(pedfile)

    assert model.columnCount() == 6
    assert model.rowCount() == 2

    # Test output
    outfile = tempfile.mkstemp(suffix=".ped", text=True)[1]
    model.to_pedfile(outfile)
    # Since test file have an erroneous sample, the 2 files are different
    assert not filecmp.cmp(outfile, pedfile)

    with open(pedfile, "r") as ref_file, open(outfile, "r") as found_file:
        # Read first 2 lines
        expected_lines = "".join([next(ref_file) for _ in range(2)])
        found_lines = found_file.read()

        print("expected:\n'" + expected_lines + "'")
        print("found:\n'" + found_lines + "'")

    assert expected_lines == found_lines

    qtmodeltester.check(model)
