import unittest2
from bitarray import bitarray
from bitarray.util import ba2hex
from mot import CharacterSet, ContentName, MimeType, AbsoluteExpiration, RelativeExpiration, Compression, Priority, DefaultPermitOutdatedVersions, CompressionType
from datetime import datetime, timedelta

class HelperMethodsTest(unittest2.TestCase):
    pass

class ContentNameTest(unittest2.TestCase):
    
    def test_contentname_latin1(self):
        name = ContentName('TEST')
        hex = 'cc054054455354'

        assert name.tobytes().hex() == hex
        
    def test_contentname_utf(self):
        name = ContentName('TEST', charset=CharacterSet.ISO_IEC_10646)
        hex = 'cc05f054455354'

        assert name.tobytes().hex() == hex
        
class MimeTypeTest(unittest2.TestCase):
    
    def test_mimetype(self):
        mimetype = MimeType("image/png")

        assert mimetype.tobytes().hex() == 'd009696d6167652f706e67'
        
class ExpirationTest(unittest2.TestCase):
    
    def test_expire_in_5_minutes(self):
        expiration = RelativeExpiration(timedelta(minutes=5))
        hex = '4402'
        
        assert expiration.tobytes().hex() == hex
        
    def test_expire_at_set_date_shortform(self):
        expiration = AbsoluteExpiration(datetime(2010, 8, 11, 12, 34, 0 ,0))
        hex = '84b61ec322'
        
        assert expiration.tobytes().hex() == hex
        
    def test_expire_at_set_date_longform(self):
        expiration = AbsoluteExpiration(datetime(2010, 8, 11, 12, 34, 11, 678000))
        hex = 'c406b61ecb222ea6'

        assert expiration.tobytes().hex() == hex
        
class CompressionTypeTest(unittest2.TestCase):
    
    def test_gzip(self):
        param = Compression(type=CompressionType.GZIP)

        assert param.tobytes().hex() == '5101'

        
class PriorityTest(unittest2.TestCase):
    
    def test_priority(self):
        param = Priority(4)
        hex = '4a04'

        assert param.tobytes().hex() == hex
        
class DefaultPermitOutdatedVersionsTest(unittest2.TestCase):
    
    def test_permitted(self):
        param = DefaultPermitOutdatedVersions(True)

        assert param.tobytes().hex() == '4101'

    def test_forbidden(self):
        param = DefaultPermitOutdatedVersions(False)
        
        assert param.tobytes().hex() == '4100'


if __name__ == "__main__":
    unittest2.main()
