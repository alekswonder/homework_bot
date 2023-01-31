from json.decoder import JSONDecodeError


class BadResponseExtension(Exception):
    """Subclass of base exception class that specifies bad response status"""
    pass


class InvalidJSONExtension(JSONDecodeError):
    """Subclass of JSONDecodeError(ValueError) that specifies invalid JSON"""
    pass
