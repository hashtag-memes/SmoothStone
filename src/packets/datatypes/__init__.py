try:
    from simple import *
    from complex import *
except ImportError:
    from .simple import *
    from .complex import *