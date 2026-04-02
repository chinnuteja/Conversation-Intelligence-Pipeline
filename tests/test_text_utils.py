from src.text_utils import strip_code_fences


def test_strip_code_fences():
    assert strip_code_fences('{"a": 1}') == '{"a": 1}'
    raw = "```json\n{\"x\": 1}\n```"
    assert strip_code_fences(raw) == '{"x": 1}'
