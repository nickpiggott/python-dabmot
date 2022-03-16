import unittest2
from bitarray import bitarray
from bitarray.util import ba2hex
from mot import MotObject, ContentType, MimeType, AbsoluteExpiration
from datetime import datetime

class MotObjectEncodingTest(unittest2.TestCase):
    
    def test_simple_1(self):

        # create MOT object
        object = MotObject("TestObject", "\x00" * 16, ContentType.IMAGE_JFIF)

    def test_simple_2(self):

        # create MOT object
        object = MotObject("TestObject", "\x00" * 16, ContentType.IMAGE_JFIF)        

        # add additional parameter - mimetype and absolute expiration
        object.add_parameter(MimeType("image/jpg"))
        object.add_parameter(AbsoluteExpiration(datetime(2010, 8, 11, 12, 34, 11, 678000)))
        
        tmp = bitarray()
        tmp.frombytes(b'\x51\x01')
        assert object.encode() == tmp
    

if __name__ == "__main__":
    unittest2.main()
