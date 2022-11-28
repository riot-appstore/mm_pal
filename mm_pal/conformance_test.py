"""A conformance test to ensure devices adhere to the the specifications."""
from collections import ChainMap
from mm_pal.mm_if import MmIf


class BaseConformanceSuite:
    """Base class for conformance tests."""

    def target(self) -> MmIf:  # pragma: no cover
        """Target to test, overridden by device."""
        raise NotImplementedError

    def test_read_reg(self, target: MmIf):
        """Read all registers."""
        for key, val in target.mem_map.items():
            res = target.read_reg(key)
            if val.get('default'):
                assert val.get('default') == res

    def test_read_struct(self, target: MmIf):
        """Read only structs."""
        regs = {}
        for key in target.mem_map.keys():
            name = key.split('.')
            if len(name) > 1:
                if name[0] not in regs:
                    regs[name[0]] = []
                if not key.endswith('.res') and not key.endswith('.padding'):
                    regs[name[0]].append(key)
        for key, reg_names in regs.items():
            res = dict(ChainMap(*target.read_struct(key)))

            for reg_name in reg_names:
                if self._consistent_reg(target, reg_name):
                    assert res[reg_name] == target.read_reg(reg_name)

    def test_write_reg(self, target: MmIf):
        """Write all registers."""
        for key, val in target.mem_map.items():
            try:
                if val['access'] & self.resolved_write_permission:
                    res = target.read_reg(key)
                    res = target.write_reg(key, res)
            except AttributeError:
                res = target.read_reg(key)
                res = target.write_reg(key, res)

    def _consistent_reg(self, target: MmIf, reg_name):
        """Check if a register can be consistently read."""
        flags = target.mem_map[reg_name].get('flag', "").split()
        if "VOLATILE" in flags:
            return False
        if "DEVICE_SPECIFIC" in flags:
            return False
        return True
