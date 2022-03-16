import unittest2
from bitarray import bitarray
from bitarray.util import ba2hex
from mot import ContentName, MimeType, AbsoluteExpiration, RelativeExpiration, Compression, Priority, DefaultPermitOutdatedVersions, bitarray_to_hex
from datetime import datetime, timedelta

class ContentNameTest(unittest2.TestCase):
    
    def test_contentname_latin1(self):
        name = ContentName('TEST')

        tmp = bitarray()
        tmp.frombytes(b'\xCC\x05\x40\x54\x45\x53\x54')
        assert name.encode() == tmp
        
    def test_contentname_utf(self):
        name = ContentName('TEST', charset=ContentName.ISO_IEC_10646)

        tmp = bitarray()
        tmp.frombytes(b'\xCC\x05\xF0\x54\x45\x53\x54')
        assert name.encode() == tmp
        
class MimeTypeTest(unittest2.TestCase):
    
    def test_mimetype(self):
        mimetype = MimeType("image/png")
        
        tmp = bitarray()
        tmp.frombytes(b'\xD0\x09\x69\x6D\x61\x67\x65\x2F\x70\x6E\x67')
        assert mimetype.encode() == tmp
        
class ExpirationTest(unittest2.TestCase):
    
    def test_expire_in_5_minutes(self):
        expiration = RelativeExpiration(timedelta(minutes=5))

        tmp = bitarray()
        tmp.frombytes(b'\x44\x02')
        assert expiration.encode() == tmp
        
    def test_expire_at_set_date_shortform(self):
        expiration = AbsoluteExpiration(datetime(2010, 8, 11, 12, 34, 0 ,0))

        tmp = bitarray()
        tmp.frombytes(b'\x84\xB6\x1E\xC3\x22')     
        assert expiration.encode() == tmp
        
    def test_expire_at_set_date_longform(self):
        expiration = AbsoluteExpiration(datetime(2010, 8, 11, 12, 34, 11, 678000))

        tmp = bitarray()
        tmp.frombytes(b'\xC4\x06\xB6\x1E\xCB\x22\x2E\xA6')
        assert expiration.encode() == tmp
        
class CompressionType(unittest2.TestCase):
    
    def test_gzip(self):
        param = Compression.GZIP

        tmp = bitarray()
        tmp.frombytes(b'\x51\x01')
        assert param.encode() == tmp

        
class PriorityTest(unittest2.TestCase):
    
    def test_priority(self):
        param = Priority(4)

        tmp = bitarray()
        tmp.frombytes(b'\x4A\x04')
        assert param.encode() == tmp
        
class DefaultPermitOutdatedVersionsTest(unittest2.TestCase):
    
    def test_permitted(self):
        param = DefaultPermitOutdatedVersions(True)

        assert ba2hex(param.encode()) == '4101'

    def test_forbidden(self):
        param = DefaultPermitOutdatedVersions(False)
        
        assert ba2hex(param.encode()) == '4100'


if __name__ == "__main__":
    unittest2.main()
