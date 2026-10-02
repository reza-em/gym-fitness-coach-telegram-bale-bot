"""Platform selection (no dependencies): env FITNESS_PLATFORM=telegram|bale (default telegram).
One process per platform; each has its own SQLite file / lock / log (user ids differ between the platforms, so data is per platform).
Everything else (program, nutrition, charts, UI, tests) is shared code."""
import os, sys

BASE = os.path.dirname(os.path.abspath(__file__))

class Plat:
    def __init__(self, name):
        self.name = name
        if name == "bale":
            self.label = "بله"; self.token_env = "FITNESS_BALE_BOT_TOKEN"
            self.api_base = "https://tapi.bale.ai"
            self.link_host = "ble.ir"
            suffix = "_bale"
            self.profile = False        # Bale: only setMyCommands works (name/description are set in Bale's @botfather)
            self.markdown = True        # no parse_mode on Bale: we convert our HTML subset to Markdown
            self.claim = True           # owner proves identity with a one-time code (usernames are not proof of identity)
        else:
            self.label = "تلگرام"; self.token_env = "FITNESS_TELEGRAM_BOT_TOKEN"
            self.api_base = "https://api.telegram.org"
            self.link_host = "t.me"
            suffix = ""
            self.profile = True; self.markdown = False; self.claim = False
        self.token = os.environ.get(self.token_env, "")
        self.db_path = os.environ.get("FITNESS_DB_PATH") or os.path.join(BASE, "fitness%s.db" % suffix)
        self.lock_name = "bot%s.lock" % suffix
        self.log_name = "bale.log" if name == "bale" else "bot.log"

    @property
    def api(self): return f"{self.api_base}/bot{self.token}/"
    def link(self, username): return f"https://{self.link_host}/{username}"

NAME = (os.environ.get("FITNESS_PLATFORM") or "telegram").strip().lower()
if NAME not in ("telegram", "bale"):
    print("unknown FITNESS_PLATFORM=%r (telegram|bale)" % NAME, file=sys.stderr); sys.exit(1)
PLAT = Plat(NAME)
IS_BALE = NAME == "bale"

def all_tokens():
    """Both platforms' tokens (for log redaction no matter which platform runs)."""
    return [t for t in (os.environ.get("FITNESS_TELEGRAM_BOT_TOKEN", ""), os.environ.get("FITNESS_BALE_BOT_TOKEN", "")) if t]
