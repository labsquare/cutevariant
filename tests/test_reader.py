from cutevariant.core.reader import VcfReader
import vcf
import os


def test_vcf():
    filename = "exemples/test.vcf"
    # assert os.path.exists(filename), "file doesn't exists"

    MAX_VARIANTS = 10
    GENOTYPE = {"1/1": 2, "1/0": 1, "0/0": 0}

    # Import using pyvcf
    with open(filename, "r") as file:
        other_reader = vcf.Reader(file)
        fields = [i for i in other_reader.infos]  # Plus tard

        # Take some variants
        other_variants = []
        for i, variant in enumerate(other_reader):
            other_variants.append(variant)
            if i >= MAX_VARIANTS:
                break

                # import using cutevariant
    with open(filename, "r") as file:
        my_reader = VcfReader(file)


        assert my_reader.get_variants_count() == 902
        assert my_reader.get_samples() == other_reader.samples

        fields = [f["name"] for f in my_reader.get_fields()]

        assert "chr" in fields
        assert "pos" in fields
        assert "ref" in fields
        assert "alt" in fields

        # TODO : test annotation .. Gloups ..

        # Take some variants
        my_variants = []
        for i, variant in enumerate(my_reader.get_variants()):
            my_variants.append(variant)
            if i >= MAX_VARIANTS:
                break

                # test each variants
        for i, variant in enumerate(my_variants):
            assert variant["chr"] == other_variants[i].CHROM
            assert variant["pos"] == other_variants[i].POS
            assert variant["ref"] == other_variants[i].REF

            # Test if samples exists
            if len(other_variants[i].samples) != 0:
                other_sample = other_variants[i].samples[0].sample
                other_gt = other_variants[i].samples[0]["GT"]

                assert variant["samples"][0]["gt"] == GENOTYPE.get(other_gt, -1)
