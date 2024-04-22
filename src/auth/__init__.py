try:
    from microsoft_auth import MicrosoftAuth
    from profile import Profile
except ImportError:
    from .microsoft_auth import MicrosoftAuth
    from .profile import Profile