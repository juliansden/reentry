"""Field widths, masks, and limits for the CCSDS Space Packet Protocol (133.0-B-2)."""

PRIMARY_HEADER_SIZE = 6  # octets

# Field bit widths within the 6-octet primary header.
VERSION_BITS = 3
TYPE_BITS = 1
SEC_HDR_FLAG_BITS = 1
APID_BITS = 11
SEQ_FLAGS_BITS = 2
SEQ_COUNT_BITS = 14
PACKET_DATA_LENGTH_BITS = 16

VERSION_MAX = (1 << VERSION_BITS) - 1
APID_MAX = (1 << APID_BITS) - 1  # 2047; 0x7FF is the reserved "idle" APID
APID_IDLE = APID_MAX
SEQ_FLAGS_MAX = (1 << SEQ_FLAGS_BITS) - 1
SEQ_COUNT_MAX = (1 << SEQ_COUNT_BITS) - 1
PACKET_DATA_LENGTH_MAX = (1 << PACKET_DATA_LENGTH_BITS) - 1  # 65535

# Sequence flags values.
SEQ_FLAGS_CONTINUATION = 0b00
SEQ_FLAGS_FIRST = 0b01
SEQ_FLAGS_LAST = 0b10
SEQ_FLAGS_UNSEGMENTED = 0b11

# The correct value for the version field per the spec (all current versions use 0).
VERSION_CCSDS = 0

# Packet data length field encodes (total octets following primary header) - 1,
# so the maximum representable packet is header + 65536 octets of data.
MAX_PACKET_DATA_LENGTH = PACKET_DATA_LENGTH_MAX + 1
MAX_PACKET_SIZE = PRIMARY_HEADER_SIZE + MAX_PACKET_DATA_LENGTH
