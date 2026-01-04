from unifi_network_maps.io.export import write_output


def test_write_output_defaults_to_stdout(capsys):
    write_output("hello", output_path=None, stdout=False)
    assert capsys.readouterr().out == "hello"


def test_write_output_writes_file(tmp_path):
    path = tmp_path / "out.txt"
    write_output("content", output_path=str(path), stdout=False)
    assert path.read_text(encoding="utf-8") == "content"
