from cutevariant.gui.model_view import *

import filecmp
import tempfile


def test_pedmodel(qtmodeltester):
    model = PedModel()

    pedfile = "examples/test.snpeff.pedigree.tfam"

    assert model.rowCount() == 0

    model.from_pedfile(pedfile)

    assert model.columnCount() == 6
    assert model.rowCount() == 2

    # Test output
    outfile = tempfile.mkstemp(suffix=".ped", text=True)[1]
    model.to_pedfile(outfile)
    assert filecmp.cmp(outfile, pedfile) == True

    qtmodeltester.check(model)
