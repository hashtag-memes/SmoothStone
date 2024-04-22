from auth import MicrosoftAuth

auth = MicrosoftAuth(True)
auth.start()
print(auth.profile)