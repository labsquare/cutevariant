from cutevariant import commons as cm
import tempfile
import json


def test_bytes_to_readable():

    assert cm.bytes_to_readable(1024) == "1.0KB"
    assert cm.bytes_to_readable(2048) == "2.0KB"
    assert cm.bytes_to_readable(1_048_576) == "1.0MB"
    assert cm.bytes_to_readable(1_073_741_824) == "1.0GB"
    assert cm.bytes_to_readable(1_099_511_627_776) == "1.0TB"


def test_snake_to_camel():

    assert cm.snake_to_camel("query_view") == "QueryView"
    assert cm.snake_to_camel("query_test_view") == "QueryTestView"


def test_camel_to_snake():
    assert cm.camel_to_snake("QueryView") == "query_view"
    assert cm.camel_to_snake("getValue") == "get_value"


def test_is_json_file():
    _, filename = tempfile.mkstemp(suffix=".json")

    print(filename)

    with open(filename, "w") as file:
        json.dump({"name": "age"}, file)

    assert cm.is_json_file(filename) == True
    assert cm.is_json_file("nofile.png") == False


def test_uncompress_size():

    assert cm.get_uncompressed_size("examples/test.snpeff.vcf") == 23718
    assert cm.get_uncompressed_size("examples/test.snpeff.vcf.gzip.gz") == 23718
    assert cm.get_uncompressed_size("examples/test.snpeff.vcf.bgzip.gz") == 23718
