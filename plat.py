"""Platform selection (no dependencies).

Polling mode (bot.py): env FITNESS_PLATFORM=telegram|bale (default telegram) - one process per platform,
each with its own SQLite file / lock / log (user ids differ between the platforms, so data is per platform).

Serverless/webhook mode (api/index.py): ONE process serves both platforms, so the active platform is chosen
per request with `plat.use("bale")` (a contextvar). `PLAT` is a proxy that always resolves to the platform
active in the current context, so existing `PLAT.token`, `PLAT.label`, `PLAT.is_bale` ... calls keep working.
Everything else (program, nutrition, charts, UI, tests) is shared code."""
import os, sys, contextvars
from contextlib import contextmanager

BASE = os.path.dirname(os.path.abspath(__file__))
NAMES = ("telegram", "bale")
SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("FITNESS_SERVERLESS"))

class Plat:
    def __init__(self, name):
        self.name = name
        self.is_bale = name == "bale"
        if self.is_bale:
            self.label = "بله"; self.token_env = "FITNESS_BALE_BOT_TOKEN"
            self.api_base = os.environ.get("FITNESS_BALE_API_BASE") or "https://tapi.bale.ai"
            self.link_host = "ble.ir"
            suffix = "_bale"
            self.profile = False        # Bale: only setMyCommands works (name/description are set in Bale's @botfather)
            self.markdown = True        # no parse_mode on Bale: we convert our HTML subset to Markdown
            self.claim = True           # owner proves identity with a one-time code (usernames are not proof of identity)
        else:
            self.label = "تلگرام"; self.token_env = "FITNESS_TELEGRAM_BOT_TOKEN"
            self.api_base = os.environ.get("FITNESS_TELEGRAM_API_BASE") or "https://api.telegram.org"   # override: local Bot API server / tests
            self.link_host = "t.me"
            suffix = ""
            self.profile = True; self.markdown = False; self.claim = False
        self.suffix = suffix
        # Local SQLite file. Serverless: the code bundle is read-only, only /tmp is writable (and ephemeral!) -
        # real deployments set TURSO_DATABASE_URL(_BALE) instead (see db.py / DEPLOY_VERCEL.md).
        default_dir = os.environ.get("FITNESS_DATA_DIR") or ("/tmp" if SERVERLESS else BASE)
        self.db_path = os.environ.get("FITNESS_DB_PATH") or os.path.join(default_dir, "fitness%s.db" % suffix)
        # Turso / libSQL (remote) database for this platform; empty -> local SQLite file above.
        if self.is_bale:
            self.turso_url = os.environ.get("TURSO_DATABASE_URL_BALE", "").strip()
            self.turso_token = (os.environ.get("TURSO_AUTH_TOKEN_BALE") or os.environ.get("TURSO_AUTH_TOKEN") or "").strip()
        else:
            self.turso_url = os.environ.get("TURSO_DATABASE_URL", "").strip()
            self.turso_token = os.environ.get("TURSO_AUTH_TOKEN", "").strip()
        self.lock_name = "bot%s.lock" % suffix
        self.log_name = "bale.log" if self.is_bale else "bot.log"

    @property
    def token(self): return os.environ.get(self.token_env, "")
    @property
    def api(self): return f"{self.api_base}/bot{self.token}/"
    def link(self, username): return f"https://{self.link_host}/{username}"
    def __repr__(self): return "<Plat %s>" % self.name

NAME = (os.environ.get("FITNESS_PLATFORM") or "telegram").strip().lower()
if NAME not in NAMES:
    print("unknown FITNESS_PLATFORM=%r (telegram|bale)" % NAME, file=sys.stderr); sys.exit(1)

_PLATS = {}
def get(name):
    """The Plat object for `name` (cached)."""
    if name not in NAMES: raise ValueError("unknown platform %r" % name)
    p = _PLATS.get(name)
    if p is None: p = _PLATS[name] = Plat(name)
    return p

_current = contextvars.ContextVar("fitness_platform", default=NAME)
def current(): return get(_current.get())

@contextmanager
def use(name):
    """Run a block (one webhook update / one cron tick) as platform `name`."""
    tok = _current.set(get(name).name)
    try: yield current()
    finally: _current.reset(tok)

class _PlatProxy:
    """Attribute access is forwarded to the platform active in the current context."""
    __slots__ = ()
    def __getattr__(self, a): return getattr(current(), a)
    def __repr__(self): return "<PLAT -> %s>" % current().name

PLAT = _PlatProxy()
IS_BALE = NAME == "bale"     # process default only (polling mode / tests); request code must use PLAT.is_bale

def is_bale(): return current().is_bale

def all_tokens():
    """Both platforms' tokens (for log redaction no matter which platform runs)."""
    return [t for t in (os.environ.get("FITNESS_TELEGRAM_BOT_TOKEN", ""), os.environ.get("FITNESS_BALE_BOT_TOKEN", "")) if t]
