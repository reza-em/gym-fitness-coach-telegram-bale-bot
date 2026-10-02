"""Central constants. Tokens come ONLY from the environment (never printed/logged)."""
import os
from plat import PLAT, BASE

BOT_NAME = "مربی بدنسازی | Fitness Coach"
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "example_owner")
OWNER_ID = int(os.environ.get("OWNER_ID", "0") or 0)            # Telegram numeric id. On Bale the owner binds with /claim <one-time code from bale.log>
DB_PATH = PLAT.db_path
ASSETS = os.path.join(BASE, "assets")
FONT_REG = os.path.join(ASSETS, "Vazirmatn-Regular.ttf")
FONT_BOLD = os.path.join(ASSETS, "Vazirmatn-Bold.ttf")

DEFAULT_TZ = "Asia/Tehran"
TIMEZONES = ["Asia/Tehran", "Asia/Dubai", "Europe/Istanbul", "Europe/Berlin", "Europe/London", "America/New_York", "UTC"]

# program / goals
PROGRAM_WEEKS = 8
DEFAULT_TARGET_DAYS = 56          # "back to ~73 kg in 2 months" (the user's wish)
REAL_RATE_LO, REAL_RATE_HI = 0.5, 1.0     # realistic gain kg/week (male); see rates()
SURPLUS_DEFAULT = 450             # kcal/day above maintenance (male 400-500)
SURPLUS_MIN, SURPLUS_MAX = 150, 900
PROTEIN_GK = 2.0                  # g/kg (male 1.8-2.2)
# per-sex numbers: realistic lean-gain rate (kg/week), starting surplus, surplus bounds, protein g/kg (default + options)
SEX = {
 "m": dict(rate=(0.5, 1.0), surplus=450, bounds=(150, 900), protein=2.0, protein_opts=(1.8, 2.0, 2.2), low=0.25, vlow=0.10, low_d=(150, 200), high=1.0, vhigh=1.3, high_d=(150, 200), label="مرد"),
 "f": dict(rate=(0.25, 0.5), surplus=300, bounds=(100, 500), protein=1.8, protein_opts=(1.6, 1.8, 2.0), low=0.12, vlow=0.05, low_d=(100, 150), high=0.6, vhigh=0.8, high_d=(100, 150), label="زن"),
}
def sx(sex): return SEX["f" if sex == "f" else "m"]
def rates(sex): return sx(sex)["rate"]
WEIGHT_QUICK = (5, 10, 15, 20, 25)

# limits
PRIVATE_MSGS_PER_MIN = 60
REMIND_MAX_LATE_MIN = 180
BROADCAST_PER_SEC = 15

ADMIN_NOTE = "owner"
