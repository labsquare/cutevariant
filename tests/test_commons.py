from cutevariant import commons as cm


def test_bytes_to_readable():

	assert cm.bytes_to_readable(1024) == "1.0KB"
	assert cm.bytes_to_readable(2048) == "2.0KB"
	assert cm.bytes_to_readable(1_048_576 ) == "1.0MB"
	assert cm.bytes_to_readable(1_073_741_824 ) == "1.0GB"
	assert cm.bytes_to_readable(1_099_511_627_776) == "1.0TB"

