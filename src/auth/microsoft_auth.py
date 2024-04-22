"""
Microsoft Authentication

Modification of https://github.com/axieum/authme/blob/main/src/main/java/me/axieum/mcmod/authme/api/util/MicrosoftUtils.java
"""

import requests
import random
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

try:
    from .profile import Profile
    from ..log import logger
except ImportError:
    from src.auth.profile import Profile
    from src.log import logger

__all__ = ["MicrosoftAuth"]

class OAuthServer(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def log_request(self, code = "-", size = "-"): pass

    def do_GET(self):
        if self.path.startswith("/callback"):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            self.server.code = params["code"][0]
            self.server.state = params["state"][0]
            self.server.error = params.get("error", [None])[0]
            self.server.error_description = params.get("error_description", [None])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            try:
                self.end_headers()
            except AttributeError:
                pass
            self.wfile.write(b"""\
<!doctype html>
<html>
    <head>
        <title>Authentication Complete!</title>
    </head>
    <body>
        <h1>Authentication Complete!</h1>
        <br>
        You can now close this page.
    </body>
</html>
            """)

            self.server._BaseServer__shutdown_request = True

    @classmethod
    def run(cls, port: int, state: str):
        addr = ('', port)
        httpd = HTTPServer(addr, cls)
        httpd.serve_forever()

        return httpd.code, httpd.state, httpd.error, httpd.error_description

class MicrosoftAuth:
    CLIENT_ID = "e16699bb-2aa8-46da-b5e3-45cbcce29091"
    AUTHORIZE_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
    XBOX_AUTH_URL = "https://user.auth.xboxlive.com/user/authenticate"
    XBOX_XSTS_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
    MC_AUTH_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"
    MC_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"
    PORT = 25585
    PROMPT_TYPE = "select_account"

    def __init__(self, write_stdout=False, write_file=True, open_ms_auth=True):
        self.profile = Profile("", "", "")
        self.open_ms_auth = open_ms_auth
        self.LOGGER = logger("MicrosoftAuth", write_stdout, write_file)

    def start(self):
        auth_code = self.get_microsoft_auth_code()
        if auth_code is None:
            return

        ms_access_token = self.get_microsoft_access_token(auth_code)
        if ms_access_token is None:
            return

        xbox_access_token = self.get_xbox_access_token(ms_access_token)
        if xbox_access_token is None:
            return

        xsts_token, user_hash = self.get_xsts_token(xbox_access_token)
        if xsts_token is None or user_hash is None:
            return

        access_token = self.get_minecraft_token(xsts_token, user_hash)
        if access_token is None:
            return

        uuid, username = self.get_minecraft_profile(access_token)
        if uuid is None or username is None:
            return

        self.profile = Profile(uuid, username, access_token)


    def get_microsoft_auth_code(self):
        self.LOGGER.info("Getting access code")
        state = "".join(random.choices("0123456789abcdefghijklmnopqrstuvwxyz", k=8))

        parameters = {
            "client_id": self.CLIENT_ID,
            "response_type": "code",
            "redirect_uri": f"http://localhost:{self.PORT}/callback",
            "scope": "XboxLive.signin offline_access",
            "state": state
        }
        if self.PROMPT_TYPE:
            parameters["prompt"] = self.PROMPT_TYPE
        uri = self.AUTHORIZE_URL + "?" + urlencode(parameters)
        self.LOGGER.info("Launching Minecraft login in browser:\n\t" + uri)
        if self.open_ms_auth:
            __import__("webbrowser").open(uri)

        server = OAuthServer
        self.LOGGER.info(f"Listening on port {self.PORT} with state {state!r}")

        try:
            code, received_state, error, error_description = server.run(self.PORT, state)
            if state != received_state:
                self.LOGGER.error(f"State mismatch! Expected {state}, received {received_state}!")
                return
            if error:
                self.LOGGER.error(f"Error! {error}: {error_description}")
                return
            if not code:
                self.LOGGER.error("Did not receive an auth code!")
                return

            self.LOGGER.info(f"Received Microsoft auth code! {code[:32]}...")
            return code

        except KeyboardInterrupt:
            self.LOGGER.error("Acquiring Microsoft auth code was cancelled!")
            return

        except Exception as e:
            self.LOGGER.error(f"Error! {e.__class__}: {e}")
            return

    def get_microsoft_access_token(self, auth_code: str):
        self.LOGGER.info("Getting access token from Microsoft")
        data = {
            "client_id": self.CLIENT_ID,
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": f"http://localhost:{self.PORT}/callback"
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        try:
            response = requests.post(self.TOKEN_URL, data=urlencode(data), headers=headers)
            json = response.json()
            if access_token := json.get("access_token"):
                self.LOGGER.info(f"Obtained access token! {access_token[:32]}...")
                return access_token
            if error := json.get("error"):
                description = json.get("error_description")
                self.LOGGER.error(f"Error! {error}: {description}")
                return
            else:
                self.LOGGER.error("Did not receive an access token!")
                return

        except KeyboardInterrupt:
            self.LOGGER.error("Acquiring access token was cancelled!")
            return

        except Exception as e:
            self.LOGGER.error(f"Error! {e.__class__}: {e}")
            return

    def get_xbox_access_token(self, access_token: str):
        self.LOGGER.info("Getting XBox Live access token")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": ""
        }
        data = {
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": f"d={access_token}"
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT"
        }

        try:
            response = requests.post(self.XBOX_AUTH_URL, json=data, headers=headers)
            response_json = response.json()
            if token := response_json.get("Token"):
                self.LOGGER.info(f"Obtained XBox Live access token! {token[:32]}...")
                return token

            if error := response_json.get("XErr"):
                self.LOGGER.error(f"Error! {error}: {response_json["Message"]}")
                return
            else:
                self.LOGGER.error("Did not receive an access token!")
                return

        except KeyboardInterrupt:
            self.LOGGER.error("Acquiring access token was cancelled!")
            return

        except Exception as e:
            self.LOGGER.error(f"Error! {e.__class__.__name__}: {e}")
            return

    def get_xsts_token(self, access_token: str):
        self.LOGGER.info("Getting XBox Live XSTS token")
        headers = {
            "Content-Type": "application/json"
        }
        data = json.dumps({
            "Properties": {
                "SandboxId": "RETAIL",
                "UserTokens": [access_token]
            },
            "RelyingParty": "rp://api.minecraftservices.com/",
            "TokenType": "JWT"
        })

        try:
            response = requests.post(self.XBOX_XSTS_URL, data=data, headers=headers)
            response_json = response.json()

            if (token := response_json.get("Token")) and (uhs := response_json.get("DisplayClaims", {}).get("xui", [{}])[0].get("uhs")):
                self.LOGGER.info(f"Obtained XBox Live XSTS token! {token[:32]}...")
                self.LOGGER.info(f"Obtained user hash! {uhs}")
                return token, uhs

            if error := response_json.get("XErr"):
                errors = {
                    2148916233: "This account does not have an XBox account!",
                    2148916235: "XBox Live is banned in your country!",
                    2148916236: "This account requires adult verification on XBox page!",
                    2148916237: "This account requires adult verification on XBox page!",
                    2148916238: "This account is a child unless added to Family!"
                }
                self.LOGGER.error(f"Error! {errors[error]}")
                return None, None
            else:
                self.LOGGER.error("Did not receive an XSTS token!")
                return None, None

        except KeyboardInterrupt:
            self.LOGGER.error("Acquiring XSTS token was cancelled!")
            return None, None

        except Exception as e:
            self.LOGGER.error(f"Error! {e.__class__}: {e}")
            return None, None

    def get_minecraft_token(self, xsts_token: str, uhs: str):
        self.LOGGER.info("Getting Minecraft access token")
        headers = {
            "Content-Type": "application/json"
        }
        data = json.dumps({
            "identityToken": f"XBL 3.0 x={uhs};{xsts_token}"
        })

        try:
            response = requests.post(self.MC_AUTH_URL, data=data, headers=headers)
            response_json = response.json()

            if token := response_json.get("access_token"):
                self.LOGGER.info(f"Acquired Minecraft access token! {token[:32]}...")
                return token

            if error := response_json.get("error"):
                self.LOGGER.error(f"Error! {error}: {response_json["errorMessage"]}")
                return
            else:
                self.LOGGER.error("Did not receive a Minecraft access token!")
                return

        except KeyboardInterrupt:
            self.LOGGER.error("Acquiring Minecraft access token was cancelled!")
            return

        except Exception as e:
            self.LOGGER.error(f"Error! {e.__class__}: {e}")
            return

    def get_minecraft_profile(self, access_token: str):
        self.LOGGER.info("Fetching Minecraft profile")
        headers = {
            "Authorization": "Bearer " + access_token
        }

        try:
            response = requests.get(self.MC_PROFILE_URL, headers=headers)
            response_json = response.json()

            if uuid := response_json.get("id"):
                name = response_json["name"]
                self.LOGGER.info(f"Received UUID! {uuid}")
                self.LOGGER.info(f"Received username! {name}")
                return uuid, name

            if error := response_json.get("error"):
                self.LOGGER.error(f"Error! {error}: {response_json["errorMessage"]}")
                return None, None
            else:
                self.LOGGER.error("Did not receive a Minecraft profile!")
                return None, None

        except KeyboardInterrupt:
            self.LOGGER.error("Acquiring Minecraft profile was cancelled!")
            return None, None

        except Exception as e:
            self.LOGGER.error(f"Error! {e.__class__}: {e}")
            return None, None


if __name__ == "__main__":
    MicrosoftAuth().start()
