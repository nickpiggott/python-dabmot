import unittest2

from mot import HeaderParameter
from mot.epg import ScopeId

class ScopeIdTest(unittest2.TestCase):

    def test_encode_si_scope(self):
        id = ScopeId(0xe1, 0xc185)

        assert id.tobytes().hex() == 'e718e1c185'
        #HeaderParameter.frombytes(id.tobytes())
        
    def test_pi_scope(self):
        id = ScopeId(0xe1, 0xc185, 0xc586, 0)

        assert id.tobytes().hex() == 'e73040e1c185c586'

        #HeaderParameter.from_bits(id.encode())

if __name__ == "__main__":
    unittest2.main()
