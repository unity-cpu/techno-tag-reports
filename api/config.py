import os

PLAYFAB_TITLE_ID = os.environ.get("PLAYFAB_TITLE_ID")
PLAYFAB_SECRET_KEY = os.environ.get("PLAYFAB_SECRET_KEY")
WEBHOOK_DEFAULT = os.environ.get("WEBHOOK_DEFAULT")
WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST")
WEBHOOK_SPECIAL = os.environ.get("WEBHOOK_SPECIAL", WEBHOOK_DEFAULT)
WEBHOOK_SPAM = os.environ.get("WEBHOOK_SPAM")
WEBHOOK_TRUSTED = os.environ.get("WEBHOOK_TRUSTED")

ROLE_WEBHOOKS = {
    "Illustrator": os.environ.get("WEBHOOK_ILLUSTRATOR", WEBHOOK_DEFAULT),
    "FingerPainter": os.environ.get("WEBHOOK_FINGERPAINTER", WEBHOOK_DEFAULT),
    "ForestGuide": os.environ.get("WEBHOOK_FORESTGUIDE", WEBHOOK_DEFAULT),
    "ForestLeader": os.environ.get("WEBHOOK_FORESTLEADER", WEBHOOK_DEFAULT),
    "ForestHelper": os.environ.get("WEBHOOK_FORESTHELPER", WEBHOOK_DEFAULT),
    "Trusted": os.environ.get("WEBHOOK_TRUSTED", WEBHOOK_TRUSTED),
}

NON_REPORTABLE_IDS = [
    "6F4FBE2BCA16068A",
    "B80667DDCD44DC17",
    "56BAE470B62F4CDD",
]

UNITYS_IDS          = ["6F4FBE2BCA16068A", "B80667DDCD44DC17"]
FOUNDER_IDS         = ["BF29B79A2B400090", "CEF3083A3BE0F883"]
CO_FOUNDER_IDS      = ["2A4D748DEE715B68", "56BAE470B62F4CDD"]
OWNER_IDS           = []
CO_OWNER_IDS        = []
STAFF_MANAGER_IDS   = []
PLAYFAB_MANAGER_IDS = []
COMMUNITY_MANAGER_IDS = []
HEAD_ADMIN_IDS      = []
ADMIN_IDS           = ["AD6D4E9FB44E6C0C"]
TRIAL_ADMIN_IDS     = []
HEAD_MOD_IDS        = ["5ADD21B0BF6FB425"]
MOD_IDS             = ["59FE193D73752516", "EA12FC6A4F8AF723", "DD84C718E8AFD777", "71469BA4796CD3E4"]
TRIAL_MOD_IDS       = ["4F5C99FA420D8B74"]
FOREST_LEADER_IDS   = []
ILLUSTRATOR_IDS     = []
FINGER_PAINTER_IDS  = []
FOREST_GUIDE_IDS    = []
FOREST_HELPER_IDS   = []
TRUSTED_IDS         = []

BAN_DURATIONS = {
    "Unity":              500,
    "Founder":            324,
    "CoFounder":          268,
    "Owner":              168,
    "CoOwner":             98,
    "StaffManager":        84,
    "PlayFabManager":      68,
    "CommunityManager":    64,
    "HeadAdministrator":   62,
    "Administrator":       48,
    "TrialAdministrator":  36,
    "HeadModerator":       32,
    "Moderator":           12,
    "TrialModerator":       1,
}

STAFF_DISPLAY_NAMES = {
    "6F4FBE2BCA16068A": "UNITY.LOLZ",
    "BF29B79A2B400090": "MILK",
    "7023FC96F13FDA59":  "CXV",
    "5433C00BD5343624":  "JAX",
    "DFA7A1D427017AD6":  "HASSER",
    "4AB378170F86220B":  "PLEMBA",
    "D0A30B69FA2B751B":  "PRINCESS",
}

REPORTER_SPAM_THRESHOLD  = 5
REPORTER_SPAM_WINDOW     = 60
REPORTER_SPAM_BAN_DURATION = 24
TRUSTED_BAN_DURATION     = 1
TRUSTED_REPORT_MULTIPLIER = 3
