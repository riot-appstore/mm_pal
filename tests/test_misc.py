from mm_pal import write_history_file

def test_write_history_file(mock_app_json, mm_if_inst):
    write_history_file()
    write_history_file("/tmp/test_history")
