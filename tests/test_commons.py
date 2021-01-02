from cutevariant import commons as cm


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
