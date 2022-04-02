from mot import *
from spi import DabBearer
from spi.binary import encode_ensembleid, encode_bearer, decode_contentid

class EpgContentType():
    
    # content types 
    SERVICE_INFORMATION = ContentType(7, 0)
    PROGRAMME_INFORMATION = ContentType(7, 1)
    GROUP_INFORMATION = ContentType(7, 2)

class ScopeStart(HeaderParameter):
    
    def __init__(self, start):
        HeaderParameter.__init__(self, 0x25)
        self.start = start.replace(microsecond=0)

    def encode_data(self):
        return encode_absolute_time(self.start)
    
    def __str__(self):
        return self.start.isoformat()
    
    def __repr__(self):
        return '<ScopeStart: %s>' % str(self)
    
    @staticmethod
    def decode_data(data):
        return ScopeStart(decode_absolute_time(data))

class ScopeEnd(HeaderParameter):
    
    def __init__(self, end):
        HeaderParameter.__init__(self, 0x26)
        if not isinstance(end, datetime): raise TypeError('end must be a datetime')
        self.end = end.replace(microsecond=0)

    def encode_data(self):
        return encode_absolute_time(self.end)
    
    def __str__(self):
        return self.end.isoformat()
    
    def __repr__(self):
        return '<ScopeEnd: %s>' % str(self)
    
    @staticmethod
    def decode_data(data):
        return ScopeEnd(decode_absolute_time(data))

class ScopeId(HeaderParameter):

    def __init__(self, ecc, eid, sid=None, scids=None, xpad=None):
        HeaderParameter.__init__(self, 0x27)
        self.__ecc = ecc
        self.__eid = eid
        self.__sid = sid
        self.__scids = scids
        self.__xpad = 0

    def encode_data(self):
        if self.__ecc and self.__eid and not self.__sid and not self.__scids: # ensemble ID
            return encode_ensembleid((self.__ecc, self.__eid))
        else: # DAB bearer ID
            return encode_bearer(DabBearer(self.__ecc, self.__eid, self.__sid, self.__scids))
    
    def __str__(self):
        result = []
        if (self.__ecc and self.__eid):
            return "%02x.%04x" % (self.__ecc, self.__eid)
        else:
            return "%02x.%04x.%04x.%x" % (self.__ecc, self.__eid, self.__sid, self.__scids)
    
    def __repr__(self):
        return '<ScopeId: %s>' % str(self)        
    
    @staticmethod
    def decode_data(data):
        return ScopeId(*decode_contentid(data))
    
register_header_parameter_decoder(0x25, ScopeStart.decode_data)
register_header_parameter_decoder(0x26, ScopeEnd.decode_data)
register_header_parameter_decoder(0x27, ScopeId.decode_data) 
