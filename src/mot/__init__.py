from email.header import Header
from bitarray import bitarray
from bitarray.util import ba2int, int2ba
from msc import generate_transport_id
from datetime import timedelta, datetime, time
from dateutil.tz import tzutc
from typing import List

import logging
import types
import julian

from enum import Enum

logger = logging.getLogger('mot')

class ContentType:
    '''Content type and subtypes as per ETSI TS 101 756 v1.3.1 (2006-02)'''
    
    def __init__(self, type, subtype):
        self.type = type
        self.subtype = subtype

    def __eq__(self, other):
        if not isinstance(other, ContentType): return False
        return self.type == other.type and self.subtype == other.subtype

    def __hash__(self):
        return hash('%d%d' % (self.type, self.subtype))
        
    def __str__(self):
        return '[%d:%d]' % (self.type, self.subtype)
    
# General Data
ContentType.GENERAL_OBJECT_TRANSFER = ContentType(0, 0)
ContentType.GENERAL_MIME_HTTP = ContentType(0, 1)
    
# Text
ContentType.TEXT_ASCII = ContentType(1, 0)
ContentType.TEXT_ISO = ContentType(1, 1)
ContentType.TEXT_HTML = ContentType(1, 2)
    
# Image
ContentType.IMAGE_GIF = ContentType(2, 0)
ContentType.IMAGE_JFIF = ContentType(2, 1)
ContentType.IMAGE_BMP = ContentType(2, 2)
ContentType.IMAGE_PNG = ContentType(2, 3)
    
# Audio
ContentType.AUDIO_MPEG1_L1 = ContentType(3, 0)
ContentType.AUDIO_MPEG1_L2 = ContentType(3, 1)
ContentType.AUDIO_MPEG1_L3 = ContentType(3, 2)
ContentType.AUDIO_MPEG2_L1 = ContentType(3, 3)
ContentType.AUDIO_MPEG2_L2 = ContentType(3, 4)
ContentType.AUDIO_MPEG2_L3 = ContentType(3, 5)
ContentType.AUDIO_PCM = ContentType(3, 6)
ContentType.AUDIO_AIFF = ContentType(3, 7)
ContentType.AUDIO_ATRAC = ContentType(3, 8)
ContentType.AUDIO_ATRAC2 = ContentType(3, 9)
ContentType.AUDIO_MPEG4 = ContentType(3, 10)
    
# Video
ContentType.VIDEO_MPEG1 = ContentType(4, 0)
ContentType.VIDEO_MPEG2 = ContentType(4, 1)
ContentType.VIDEO_MPEG4 = ContentType(4, 2)
ContentType.VIDEO_H263 = ContentType(4, 3)
    
# MOT Transport
ContentType.MOT_HEADER_UPDATE = ContentType(5, 0)
    
# System
ContentType.SYSTEM_MHEG = ContentType(6, 0)
ContentType.SYSTEM_JAVA = ContentType(6, 1)

__header_parameter_decoders = {}

def register_header_parameter_decoder(i, f):
    __header_parameter_decoders[i] = f
    
class HeaderParameter:
    

    def __init__(self, id):
        self.__id = id
    
    def tobytes(self) -> bytes:
        """
        Render the header preamble with the encoded data from the subclass
        """
        
        # encode the data first
        data = self.encode_data()
        data_length = len(data)
        
        # create the correct parameter preamble
        bits = bitarray()
        if data_length == 0:
            bits += int2ba(0, 2) # (0-1): PLI=0
            bits += int2ba(self.__id, 6) # (2-7): ParamId
        elif data_length == 1:
            bits += int2ba(1, 2) # (0-1): PLI=1
            bits += int2ba(self.__id, 6) # (2-7): ParamId
        elif data_length == 4:
            bits += int2ba(2, 2) # (0-1): PLI=2
            bits += int2ba(self.__id, 6) # (2-7): ParamId\
            if data_length < 4: data += bitarray((4 - data_length) * 8)
        elif data_length <= 127:
            bits += int2ba(3, 2) # (0-1): PLI=3
            bits += int2ba(self.__id, 6) # (2-7): ParamId
            bits += bitarray('0') # (8): Ext=0
            bits += int2ba(data_length, 7) # (9-15): DataFieldLength in bytes     
        elif data_length <= 32770:
            bits += int2ba(3, 2) # (0-1): PLI=3
            bits += int2ba(self.__id, 6) # (2-7): ParamId
            bits += bitarray('1') # (8): Ext=1
            bits += int2ba(data_length, 15) # (9-23): DataFieldLength in bytes 
        
        return bits.tobytes() + data
    
    def encode_data(self) -> bytes:
        raise NotImplementedError()
    
    @staticmethod
    def frombytes(data):

        bits = bitarray()
        bits.frombytes(data)                  
        
        PLI = ba2int(bits[:2])
        param_id = ba2int(bits[2:8])
        
        if PLI == 0:
            data_start = 1
            data_length = 0
        elif PLI == 1:
            data_start = 1
            data_length = 1
        elif PLI == 2:
            data_start = 1
            data_length = 4
        elif PLI == 3:
            if bits[8]:
                data_start = 3 
                data_length = ba2int(bits[9:24])
            else:
                data_start = 2 
                data_length = ba2int(bits[9:16])

        # check a good data length
        if data_length != len(data - data_start) : raise ValueError('data length %d is different from signalled data length %d' % (len(data-data_start), data_length))
        
        # check we know how to decode this
        if param_id not in HeaderParameter.decoders:
            raise UnknownHeaderParameter(param_id, data)
        decoder = HeaderParameter.decoders[param_id]
        try:
            param = decoder(data[data_start:])
            logger.debug('decoded parameter %s from param id %d with decoder %s', param, param_id, decoder)
        except:
            logger.error('error decoding parameter from content: header=%s | data=%s | using decoder: %s', 
                         data[:data_start].hex(), data[:data_start].hex(), decoder)
            raise HeaderParameterError(param_id, data)
        
        return param, data_start + data_length     

class MotObject:
    
    def __init__(self, name, body : bytes=None, contenttype : ContentType=ContentType.GENERAL_OBJECT_TRANSFER, transport_id : int=None):
        self.__parameters = {}
        if isinstance(name, str): self.add_parameter(ContentName(name))
        else: self.add_parameter(name)
        if not type(body) == bytes: raise ValueError("Body must be a byte array not %s" % type(body))
        self.__body = body
        self.__contenttype = contenttype
        self.__transport_id = transport_id if transport_id is not None else generate_transport_id(name)
        
    def add_parameter(self, param) -> None:
        if not isinstance(param, HeaderParameter): 
            raise ValueError('parameter {param} of type {type} is not a valid header parameter'.format(param=param, type=param.__class__.__name__))
        self.__parameters[param.__class__.__name__] = param
        
    def get_parameters(self) -> List[HeaderParameter]:
        return list(self.__parameters.values())
    
    def get_parameter(self, clazz) -> HeaderParameter:
        return self.__parameters.get(clazz.__name__)
    
    def has_parameter(self, clazz) -> bool:
        return self.get_parameter(clazz) is not None

    def remove_parameter(self, clazz) -> None:
        self.__parameters.pop(clazz.__name__)
    
    def get_transport_id(self) -> int:
        return self.__transport_id
    
    def get_name(self) -> str:
        return self.get_parameter(ContentName)

    def set_body(self, body : bytes) -> None:
        if not type(body) == bytes: raise ValueError("Body must be a byte array")
        self.__body = body
    
    def get_body(self) -> bytes:
        return self.__body
    
    def get_contenttype(self) -> ContentType:
        return self.__contenttype

    def __str__(self):
        return "{name} [{id}]".format(name=self.get_name(), id=self.get_transport_id())
    
def encode_absolute_time(timepoint):
  
    if timepoint is None: # NOW
        bits = bitarray(32)
        bits.setall(False)
        return bits.tobytes()
        
    bits = bitarray()
    
    # adjust for non-UTC times
    if timepoint.tzinfo is not None and timepoint.tzinfo != tzutc():
        timepoint = timepoint.astimezone(tzutc())
    
    # b0: ValidityFlag: 1 for MJD and UTC are valid
    bits += bitarray('1');
    
    # b1-17: MJD
    mjd = int(julian.to_jd(timepoint, fmt='mjd'))
    bits += int2ba(mjd, 17)
    
    # b18-19: RFU
    bits += int2ba(0, 2)

    # b20: UTC Flag
    # b21: UTC - 11 or 27 bits depending on the form
    if timepoint.second > 0:
        bits += bitarray('1')
        bits += int2ba(int(timepoint.hour), 5)
        bits += int2ba(int(timepoint.minute), 6)
        bits += int2ba(int(timepoint.second), 6)
        bits += int2ba(int(timepoint.microsecond/1000), 10)
    else:
        bits += bitarray('0')
        bits += int2ba(int(timepoint.hour), 5)
        bits += int2ba(int(timepoint.minute), 6)

    return bits.tobytes()

def decode_absolute_time(data: bytes) -> datetime:
    """
    Decode an absolute timepoint from a byte array
    """
    
    bits = bitarray()
    bits.frombytes(data)
    if not bits.any(): return None # NOW
    
    mjd = int(bits[1:18].to01(), 2)
    date = julian.from_jd(mjd, fmt='mjd')
    timepoint = datetime.combine(date, time())

    if bits[20]:
        timepoint.replace(hour=ba2int(bits[21:26]))
        timepoint.replace(minute=ba2int(bits[26:32]))
        timepoint.replace(second=ba2int(bits[32:38]))
        timepoint.replace(microsecond=ba2int(bits[38:48]) * 1000)
    else:
        timepoint.replace(hour=ba2int(bits[21:26]))
        timepoint.replace(minute=ba2int(bits[26:32]))    
    return timepoint
    
def encode_relative_time(offset):
    
    bits = bitarray()
    if offset < timedelta(minutes=127):
        minutes = int(offset.seconds / 60)
        two_minutes = int(minutes / 2) # round to multiples of 2 minutes
        bits += int2ba(0, 2) # (0-1): Granularity=0
        bits += int2ba(two_minutes, 6) # (2-7): Interval
    elif offset < timedelta(minutes=1891):
        minutes = int(offset.seconds / 60)
        halfhours = int(minutes / 30) # round to multiples of 30 minutes
        bits += int2ba(1, 2) # (0-1): Granularity=1
        bits += int2ba(halfhours, 6) # (2-7): Interval
    elif offset < timedelta(hours=127):
        hours = int(offset.seconds / (60 * 60) + offset.days * 24)
        twohours = int(hours / 2)
        bits += int2ba(2, 2) # (0-1): Granularity=2
        bits += int2ba(twohours, 6) # (2-7): Interval
    elif offset < timedelta(hours=64*24):
        days = offset.days
        bits += int2ba(2, 3) # (0-1): Granularity=3
        bits += int2ba(6, days) # (2-7): Interval
    else:
        raise ValueError('relative expiration is greater than the maximum allowed: %s > 63 days' % offset)
    
    return bits.tobytes()

def decode_relative_time(data: bytes) -> timedelta:
    """
    TODO Decode a relative time from a byte array
    """
    raise ValueError('decoding of relative time parameter not done yet')

class HeaderParameterError:

    def __init__(self, data):
        self.__data = data  

    def __str__(self):
        return "Error with header parameter data %s" % self.__data.hex()  

class UnknownHeaderParameter(HeaderParameterError):

    def __init__(self, id, data):
        HeaderParameterError.__init__(data)
        self.__id = id

    def __str__(self):
        return 'Unknown header parameter 0x%02x with size %d bytes' % (self.__id, self.__data)    

class CharacterSet(Enum):

    EBU_LATIN = 0
    EBU_LATIN_COMMON_CORE = 1
    EBU_LATIN_CORE = 2
    ISO_LATIN2 = 3
    ISO_LATIN1 = 4
    ISO_IEC_10646 = 15

class ContentName(HeaderParameter):
    """
    6.2.2.1.1 ContentName
    The parameter ContentName is used to uniquely identify an object. At any time only one object with a certain
    ContentName shall be broadcast. 
    """

    def __init__(self, name, charset=CharacterSet.ISO_LATIN1):
        HeaderParameter.__init__(self, 12)
        self.__name = name
        self.__charset = charset

    def get_name() -> str:
        return self.__name

    def get_charset() -> CharacterSet:
        return self.__charset
        
    def encode_data(self) -> bytes:
        bits = bitarray()
        bits += int2ba(self.__charset.value, 4) # (0-3): Character set indicator
        bits += int2ba(0, 4) # (4-7): RFA
        return bits.tobytes() + self.__name.encode()
    
    @staticmethod
    def decode_data(data: bytes):
        charset = CharacterSet(int((data[0] & 0b11110000) >> 4))
        return ContentName(data[1:], charset) # TODO encode to the specific character set
    
    def __str__(self):
        return self.__name
        
    def __repr__(self):
        return "<ContentName: %s>" % str(self)
    
        
class MimeType(HeaderParameter):
    """
    6.2.2.1.2 MimeType
    In HTTP, the type of an object is indicated using the Multi-purpose Internet Mail Extensions (MIME) [4] mechanism.
    MIME strings categorize object types according to first a general type followed by a specific format,
    e.g. "text/html", "image/jpeg" and "application/octet-stream".
    """

    def __init__(self, mimetype):
        HeaderParameter.__init__(self, 16)
        self.__mimetype = mimetype
        
    def encode_data(self) -> bytes:
        return self.__mimetype.encode()
    
    @staticmethod
    def decode_data(data):
        return MimeType(data.tostring())
    
class ExpirationParameter(HeaderParameter):
    
    """
    6.2.3.1.1 Expiration
    The parameter Expiration indicates how long an object can still be used by the MOT decoder after reception loss.
    The size of the DataField determines if an absolute or a relative expire time is specified
    """

    @staticmethod
    def decode_data(data):
        if len(data) == 1:
            return RelativeExpiration(decode_relative_time(data))
        elif len(data) in [4, 6]:
            return AbsoluteExpiration(decode_absolute_time(data))
        else:
            raise ValueError('unknown data length for expiration: %d bytes' % (len(data)/8))    
    
class RelativeExpiration(ExpirationParameter):
    """
    6.2.3.1.1.2
    Indicates the maximum time span an object is considered
    valid after the last time the MOT decoder could verify 
    that this object is still broadcast. 
 
    The duration can be at various levels of temporal resolution
    and covered intervals.
 
    two minutes - 2 minutes to 126 minutes
    half hours - half an hour to 31.5 hours
    two hours - 2 hours to 5 days 6 hours
    """
    
    def __init__(self, offset):
        HeaderParameter.__init__(self, 4)
        self.__offset = offset
        
    def encode_data(self) -> bytes:
        return encode_relative_time(self.__offset)
            
class AbsoluteExpiration(ExpirationParameter):
    """
    6.2.3.1.1.1
    If the size of the data field is 4 bytes or 6 bytes, then an absolute expire time is defined. 
    The value of the parameter field is coded in the UTC format (see clause 6.2.4.1). It specifies 
    the (absolute) time in UTC when the object expires. The object is not valid anymore after it 
    expired and therefore it shall no longer be presented. 
    """
 
    def __init__(self, timepoint):
        HeaderParameter.__init__(self, 4)
        self.__timepoint = timepoint
        
    def encode_data(self) -> bytes:
        return encode_absolute_time(self.__timepoint)
           
class Compression(HeaderParameter):
    '''Used to indicate that an object has been compressed and
       which compression algorithm has been applied to the data.'''
          
    def __init__(self, type):
        HeaderParameter.__init__(self, 17)
        self.__type = type
        
    def encode_data(self) -> bytes:
        return self.__type.value.to_bytes(1, byteorder='big')
    
    def __eq__(self, that):
        if not isinstance(that, Compression): return False
        return self.__type == that.__type
    
    @staticmethod
    def decode_data(data):
        return Compression(CompressionType(int.from_bytes(data)))
    
class CompressionType(Enum):
    RESERVED = 0
    GZIP = 1
        
class Priority(HeaderParameter):
    """
    6.2.3.1.4 Priority
    The parameter is used to indicate the storage priority, i.e. in case of a "memory full" state only the objects having a high
    priority should be stored.
    """
    
    def __init__(self, priority):
        if priority < 1 or priority > 255: raise ValueError("priority must be between 0 and 255, inclusive")
        HeaderParameter.__init__(self, 10)
        self.__priority = priority
        
    def encode_data(self) -> bytes:
        return self.__priority.to_bytes(1, byteorder='big')
    
    @staticmethod
    def decode_data(data):
        return Priority(int.from_bytes(data))
        
class DirectoryParameter:
    
    def __init__(self, id):
        self.__id = id
    
    def tobytes(self):
        
        # encode the data first
        data = self.encode_data()
        data_length = len(data)
        
        bits = bitarray()
        
        # create the correct parameter preamble
        if data_length == 0:
            bits += int2ba(0, 2) # (0-1): PLI=0
            bits += int2ba(self.__id, 6) # (2-7): ParamId
        elif data_length == 1:
            bits += int2ba(1, 2) # (0-1): PLI=1
            bits += int2ba(self.__id, 6) # (2-7): ParamId
        elif data_length <= 4:
            bits += int2ba(2, 2) # (0-1): PLI=2
            bits += int2ba(self.__id, 6) # (2-7): ParamId
        elif data_length <= 127:
            bits += int2ba(3, 2) # (0-1): PLI=3
            bits += int2ba(self.__id, 6) # (2-7): ParamId
            bits += bitarray('0') # (8): Ext=0
            bits += int2ba(data_length, 7) # (9-15): DataFieldLength in bytes     
        elif data_length <= 32770:
            bits += int2ba(3, 2) # (0-1): PLI=3
            bits += int2ba(self.__id, 6) # (2-7): ParamId
            bits += bitarray('1') # (8): Ext=1
            bits += int2ba(data_length, 15) # (9-23): DataFieldLength in bytes 

        return bits.tobytes() + data
    
    def encode_data(self) -> bytes:
        raise NotImplementedError()
    
    
class DefaultPermitOutdatedVersions(DirectoryParameter):
    '''When the MOT decoder notices a change to the data carousel then
       the MOT decoder must be told in the new MOT directory if an old
       version of an MOT object can be used until the new version of 
       this object is received.
  
       This parameter defines a default value for all MOT objects that
       do not provide the MOT parameter PermitOutdatedVersions.
 
       If neither parameter is provided, then the MOT decoder shall not 
       present any outdated version of this object.'''
    
    def __init__(self, permit):
        DirectoryParameter.__init__(self, 1)
        self.__permit = permit
        
    def encode_data(self):
        return b'\x01' if self.__permit else b'\x00'

class DefaultRelativeExpiration(DirectoryParameter):
    '''Used to indicate a default value that specifies how
       long an object can still be used by the MOT decoder
       after reception loss.
 
       This defines a default value for all MOT objects that do
       not provide the MOT parameter Expiration.
 
       If neither parameter is specified then the MOT object
       never expires.
 
       Indicates the maximum time span an object is considered
       valid after the last time the MOT decoder could verify 
       that this object is still broadcast. 
 
       The duration can be at various levels of temporal resolution
       and covered intervals.
 
       two minutes - 2 minutes to 126 minutes
       half hours - half an hour to 31.5 hours
       two hours - 2 hours to 5 days 6 hours'''
       
    def __init__(self, offset):
        DirectoryParameter.__init__(self, 9)
        self.__offset = offset
        
    def encode_data(self):
        return encode_relative_time(self.__offset)
    
class DefaultAbsoluteExpiration(DirectoryParameter):
    '''Used to indicate a default value that specifies how
       long an object can still be used by the MOT decoder
       after reception loss.
        
       This defines a default value for all MOT objects that do
       not provide the MOT parameter Expiration.
 
       If neither parameter is specified then the MOT object
       never expires.
 
       The value, as coded in UTC specifies the absolute time when
       the object expires. The object will not be valid anymore and 
       therefore shall no longer be presented.'''
       
    def __init__(self, timepoint):
        DirectoryParameter.__init__(self, 9)
        self.__timepoint = timepoint
        
    def encode_data(self):
        return encode_absolute_time(self.__timepoint)
    
class SortedHeaderInformation(DirectoryParameter):
    '''Used to signal that the headers within the MOT directory
       are sorted in ascending order of the ContentName
       parameter within every header information block.'''
    
    def __init__(self):
        DirectoryParameter.__init__(self, 0)
        
# register the core parameter decoders
register_header_parameter_decoder(12, ContentName.decode_data)
register_header_parameter_decoder(16, MimeType.decode_data)
register_header_parameter_decoder(4, ExpirationParameter.decode_data)
register_header_parameter_decoder(17, Compression.decode_data)
register_header_parameter_decoder(10, Priority.decode_data)
        
def is_complete(t, cache):
    
    logger.debug('checking completeness for transport id %d', t)
    
    def check_type_complete(type, transport_id=None):
        if transport_id: 
            datagroups = [x for x in cache[t] if x.get_type() == type]
            logger.debug('found %d datagroups for transport id %d type %d', len(datagroups), transport_id, type)
        else:
            datagroups = []
            for k in list(cache.keys()):
                if cache[k][0].get_type() == type: 
                    datagroups = cache[k]
                    break 
            logger.debug('found %d datagroups for type %d', len(datagroups), type)
        if not len(datagroups): return False
        previous = None
        if datagroups[0].segment_index != 0: 
            return False
        if not datagroups[-1].last: # last datagroup is not signalled last
            return False
        for d in datagroups:
            if previous and d.segment_index != previous.segment_index + 1: 
                return False
            previous = d
        return True
            
    # first check complete bodies
    if not check_type_complete(4, t):
        logger.debug('bodies for transport id %d are not complete', t) 
        return False
    
    # then check for a complete header or a complete directory
    if not check_type_complete(3, t):
        if not check_type_complete(6):
            logger.debug('no complete header and no directory available for object with transport id %s', t)
            return False
        
    return True

def decode_directory_object(data):
    
    logger.debug('decoding directory object from %d bytes of data', len(data))
    
    bits = bitarray()
    bits.frombytes(data)
    
    # parse directory header
    total_size = int(bits[2:32].to01(), 2)
    #if len(data) != total_size: raise ValueError('directory data is different from that signalled: %d != %d bytes', len(data), total_size)
    number_of_objects = int(bits[32:48].to01(), 2)
    logger.debug('directory is signalling that %d objects exist in the carousel', number_of_objects)
    carousel_period = int(bits[48:72].to01(), 2)
    if carousel_period > 0: logger.debug('carousel has a maximum rotation period of %ds', carousel_period/10)
    else: logger.debug('carousel period is undefined')
    segment_size = int(bits[75:88].to01(), 2)
    logger.debug('segment size is %d bytes', segment_size)
    directory_extension_length = int(bits[88:104].to01(), 2)
    logger.debug('directory extension length is %d bytes', directory_extension_length)

    i = 104 + (directory_extension_length * 8) # skip over the directory extenion for now
    
    logger.debug('now parsing header entries')
    headers = {}
    while i < bits.length():
        transport_id = int(bits[i:i+16].to01(), 2)
        logger.debug('parsing header with transport id %d', transport_id)
        i += 16
        
        # core header
        body_size = int(bits[i:i+28].to01(), 2)
        header_size = int(bits[i+28:i+41].to01(), 2)
        content_type = ContentType(int(bits[i+41:i+47].to01(), 2), int(bits[i+47:i+56].to01(), 2))
        logger.debug('core header indicates: body=%d bytes, header=%d bytes, content type=%s', body_size, header_size, content_type)
        end = i + (header_size * 8)
        i += 56
        
        parameters = []
        while i < end:
            try:
                parameter, size = HeaderParameter.from_bits(bits, i)
                parameters.append(parameter)
                i += (size * 8)
                logger.debug('%d bytes of header left to parse for this object', (end - i) / 8)
            except: 
                logger.exception('error parsing parameter %d bytes before the end - skipping rest of parameters', (end - i) / 8)
                i = end
                break
        headers[transport_id] = (content_type, parameters) # tuple for now
    return headers
    
def compile_object(transport_id, cache):
    
    logger.debug('compiling object with transport id %d', transport_id)
    
    params = []
    header = ''
    datagroups = cache[transport_id]

    # compile any headers for this transport ID from header objects
    for datagroup in [x for x in datagroups if x.get_type() == 3]:
        logger.debug('compiling header from datagroup %s', datagroup)
        header += datagroup.get_data() # HAVE TO BE CAREFUL HERE TO ACCOUNT FOR THE SEGMENT HEADER
        
        # parse parameters
        bits = bitarray()
        bits.frombytes(header)
        try:
            type = int(bits[41:47].to01(), 2)
            subtype = int(bits[47:56].to01(), 2)
            content_type = ContentType(type, subtype)
            logger.debug('parsed content type: %s', content_type)
            i = 56
            logger.debug('parsing header parameters')
            while i < len(bits):
                try:
                    param, size = HeaderParameter.from_bits(bits, i)
                    logger.debug('parsed header parameter: %s of size %d', param, size)
                    params.append(param)
                except UnknownHeaderParameter as e:
                    logger.warning('unknown header parameter (0x%02x) at position %d', e.id, (i/8))
                    if not e.data.length(): raise ValueError('unknown header parameter with no size - cannot continue')
                    size = e.data.length() / 8
                i += (size * 8)
        except:
            logger.error('error parsing header: \n%s' % bitarray_to_hex(bits))
            raise
        
    # or check for a directory object and get the parameters from that
    if not len(header):
        logger.debug('compiling header from directory object')
        if not cache.directory:
            directory = ''            
            for k in list(cache.keys()):
                if cache[k][0].get_type() == 6: 
                    for datagroup in cache[k]:
                        directory += datagroup.get_data()
            dir_object = decode_directory_object(directory)
            cache.directory = dir_object
        
        try:
            content_type, params = cache.directory[transport_id]
        except:
            raise
        
    # compile body
    body = ''
    for datagroup in [x for x in datagroups if x.get_type() == 4]:
        body += datagroup.get_data()
              
    name = None
    for param in params:
        if isinstance(param, ContentName): 
            name = param
    if not name: raise ValueError('no name parameter found')
        
    object = MotObject(name, body, content_type, transport_id)
    for param in params: object.add_parameter(param)
    
    # now remove the object from the cache
    cache.pop(transport_id)
      
    return object

class Cache(dict):
    def __init__(self):
        self.directory = None
        
def decode_objects(data, error_callback=None):
    """Decode a series of datagroups and yield the results.
    
    This will either be item by item if the carousel is in Header mode (i.e. once
    both header and body have been acquired), or in bursts of items once the 
    directory has been acquired
    """
        
    cache = Cache() # object cache
    logger.debug('starting to decode objects')
    
    if isinstance(data, bitarray):
        raise NotImplementedError('no support for decoding of objects from a bitarray')
    elif isinstance(data, file):
        raise NotImplementedError('no support for decoding of objects from a file object')
    elif isinstance(data, list) or isinstance(data, types.GeneratorType):
        logger.debug('decoding objects from list/generator: %s', data)
        for d in data:
            logger.debug('got datagroup: %s', d)
            items = cache.get(d.get_transport_id(), [])
            if d not in items: items.append(d)
            items = sorted(items, key=lambda x: (x.get_type(), x.segment_index))
            cache[d.get_transport_id()] = items

            # examine cache for complete objects
            for t in list(cache.keys()):
                if is_complete(t, cache):
                    logger.debug('object with transport id %d is complete', t)
                    object = compile_object(t, cache)
                    yield object
    else:
        raise ValueError('unknown object to decode from: %s' % type(data))
    logger.debug('finished')

class DirectoryEncoder:
    """TODO Encoder for MOT directories, simulates the management of a directory"""

    def __init__(self):
        self.objects = []

    def add(self, object): raise NotImplemented()

    def remove(self, object): raise NotImplemented()

    def clear(self): raise NotImplemented()

    def set(self, objects): raise NotImplemented()
