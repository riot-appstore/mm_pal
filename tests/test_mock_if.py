from mock_pal import MockIf
from conftest import EXT_PORT

def test_commands(mock_app_json):
    """Tests the serial driver using the mock device in loopback mode."""
    mockif = MockIf(port=EXT_PORT)
    mockif.get_version()
    mockif.commit()
    mockif.soft_reset()
    mockif.read_struct("stt")
    mockif.read_reg("arru8")
    mockif.write_reg("arru8", [1, 2, 3])
    mockif.special_cmd()
