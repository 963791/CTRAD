# src/utils/blacklist.py


BLACKLIST = {
'0xscamdead00000000000000000000000000000000',
'0xphishdead000000000000000000000000000000'
}


def load_blacklist():
# In production, load from file, DB, or external service
return set(addr.lower() for addr in BLACKLIST)
