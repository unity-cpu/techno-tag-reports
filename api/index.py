import json
import logging
import time
import os
from flask import Flask, request, jsonify
from datetime import datetime, timezone
import requests
from upstash_redis import Redis

from config import *

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

redis = Redis(
    url=os.environ.get("UPSTASH_REDIS_REST_URL"),
    token=os.environ.get("UPSTASH_REDIS_REST_TOKEN"),
)

CACHE_TTL = 600

ALL_ROLES = [
    "UNITYS_IDS", "FOUNDER_IDS", "CO_FOUNDER_IDS", "OWNER_IDS", "CO_OWNER_IDS",
    "STAFF_MANAGER_IDS", "PLAYFAB_MANAGER_IDS", "COMMUNITY_MANAGER_IDS",
    "HEAD_ADMIN_IDS", "ADMIN_IDS", "TRIAL_ADMIN_IDS", "HEAD_MOD_IDS",
    "MOD_IDS", "TRIAL_MOD_IDS", "FOREST_LEADER_IDS", "ILLUSTRATOR_IDS",
    "FINGER_PAINTER_IDS", "FOREST_GUIDE_IDS", "FOREST_HELPER_IDS", "TRUSTED_IDS",
]

ROLE_TO_NAME = {
    "UNITYS_IDS": "Unity", "FOUNDER_IDS": "Founder", "CO_FOUNDER_IDS": "CoFounder",
    "OWNER_IDS": "Owner", "CO_OWNER_IDS": "CoOwner", "STAFF_MANAGER_IDS": "StaffManager",
    "PLAYFAB_MANAGER_IDS": "PlayFabManager", "COMMUNITY_MANAGER_IDS": "CommunityManager",
    "HEAD_ADMIN_IDS": "HeadAdministrator", "ADMIN_IDS": "Administrator",
    "TRIAL_ADMIN_IDS": "TrialAdministrator", "HEAD_MOD_IDS": "HeadModerator",
    "MOD_IDS": "Moderator", "TRIAL_MOD_IDS": "TrialModerator",
    "FOREST_LEADER_IDS": "ForestLeader", "ILLUSTRATOR_IDS": "Illustrator",
    "FINGER_PAINTER_IDS": "FingerPainter", "FOREST_GUIDE_IDS": "ForestGuide",
    "FOREST_HELPER_IDS": "ForestHelper", "TRUSTED_IDS": "Trusted",
}

def seed_redis_if_empty():
    """Seed Redis with config.py values on first run."""
    if redis.get("seeded"):
        return
    config_ids = {
        "UNITYS_IDS": UNITYS_IDS, "FOUNDER_IDS": FOUNDER_IDS,
        "CO_FOUNDER_IDS": CO_FOUNDER_IDS, "OWNER_IDS": OWNER_IDS,
        "CO_OWNER_IDS": CO_OWNER_IDS, "STAFF_MANAGER_IDS": STAFF_MANAGER_IDS,
        "PLAYFAB_MANAGER_IDS": PLAYFAB_MANAGER_IDS, "COMMUNITY_MANAGER_IDS": COMMUNITY_MANAGER_IDS,
        "HEAD_ADMIN_IDS": HEAD_ADMIN_IDS, "ADMIN_IDS": ADMIN_IDS,
        "TRIAL_ADMIN_IDS": TRIAL_ADMIN_IDS, "HEAD_MOD_IDS": HEAD_MOD_IDS,
        "MOD_IDS": MOD_IDS, "TRIAL_MOD_IDS": TRIAL_MOD_IDS,
        "FOREST_LEADER_IDS": FOREST_LEADER_IDS, "ILLUSTRATOR_IDS": ILLUSTRATOR_IDS,
        "FINGER_PAINTER_IDS": FINGER_PAINTER_IDS, "FOREST_GUIDE_IDS": FOREST_GUIDE_IDS,
        "FOREST_HELPER_IDS": FOREST_HELPER_IDS, "TRUSTED_IDS": TRUSTED_IDS,
    }
    for role, ids in config_ids.items():
        for id_ in ids:
            redis.sadd(f"role:{role}", id_)
    for id_ in NON_REPORTABLE_IDS:
        redis.sadd("non_reportable", id_)
    redis.set("seeded", "1")

seed_redis_if_empty()

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_role_ids(role_key: str) -> set:
    members = redis.smembers(f"role:{role_key}")
    return set(members) if members else set()

def get_player_display_name(playfab_id):
    cache_key = f"name:{playfab_id}"
    cached = redis.get(cache_key)
    if cached:
        return cached
    url = f"https://{PLAYFAB_TITLE_ID}.playfabapi.com/Admin/GetUserAccountInfo"
    headers = {"X-SecretKey": PLAYFAB_SECRET_KEY, "Content-Type": "application/json"}
    try:
        resp = requests.post(url, json={"PlayFabId": playfab_id}, headers=headers, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        display_name = data.get("data", {}).get("UserInfo", {}).get("TitleInfo", {}).get("DisplayName") or "could not find"
    except Exception:
        display_name = "could not find"
    redis.set(cache_key, display_name, ex=CACHE_TTL)
    return display_name

def get_reporter_role(playfab_id):
    for role_key in ALL_ROLES:
        if playfab_id in get_role_ids(role_key):
            return ROLE_TO_NAME[role_key]
    return None

def is_host(playfab_id):
    return get_reporter_role(playfab_id) in BAN_DURATIONS

def is_insta_banned(playfab_id):
    return bool(redis.sismember("insta_bans", playfab_id))

def is_non_reportable(playfab_id):
    return bool(redis.sismember("non_reportable", playfab_id))

def send_discord_webhook(webhook_url, title=None, description=None, color=0x00FF00, content=None, footer=None, retries=3):
    if not webhook_url:
        return
    payload = {}
    if content:
        payload["content"] = content
    else:
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if footer:
            embed["footer"] = {"text": footer}
        payload["embeds"] = [embed]
    for attempt in range(retries + 1):
        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            if resp.status_code == 429:
                retry_after = float(resp.json().get("retry_after", 1)) + (2 ** attempt)
                time.sleep(retry_after)
                continue
            if resp.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            return
        except requests.exceptions.Timeout:
            time.sleep(2)
        except Exception as e:
            logging.error(f"webhook error: {e}")
            time.sleep(2)

def ban_user_playfab(playfab_id, duration_hours, reason):
    url = f"https://{PLAYFAB_TITLE_ID}.playfabapi.com/Admin/BanUsers"
    headers = {"X-SecretKey": PLAYFAB_SECRET_KEY, "Content-Type": "application/json"}
    body = {"Bans": [{"PlayFabId": playfab_id, "DurationInHours": duration_hours, "Reason": reason}]}
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logging.error(f"playfab ban failed: {e}")
        return False

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return "running."

@app.route("/report", methods=["POST"])
def handle_report():
    data = request.get_json()
    if not data:
        return jsonify({"error": "invalid json"}), 400

    reporter_id = data.get("reporter_id")
    target_id   = data.get("target_id")
    reason      = data.get("reason", "no reason provided")
    room_code   = data.get("room_code", "unknown")

    if not reporter_id or not target_id:
        return jsonify({"error": "missing reporter_id or target_id"}), 400

    reporter_role = get_reporter_role(reporter_id)
    is_trusted    = (reporter_role == "Trusted")
    is_host_flag  = is_host(reporter_id)

    if not is_trusted:
        now      = time.time()
        spam_key = f"spam:{reporter_id}:{target_id}"
        history  = redis.get(spam_key)
        timestamps = json.loads(history) if history else []
        timestamps = [t for t in timestamps if now - t <= REPORTER_SPAM_WINDOW]
        timestamps.append(now)
        redis.set(spam_key, json.dumps(timestamps), ex=REPORTER_SPAM_WINDOW)
        if len(timestamps) > REPORTER_SPAM_THRESHOLD:
            reporter_name = get_player_display_name(reporter_id)
            ban_user_playfab(reporter_id, REPORTER_SPAM_BAN_DURATION, "spam reporting same player")
            send_discord_webhook(
                WEBHOOK_SPAM,
                title="spam reporter banned",
                description=(
                    f"**Reporter:** {reporter_name}\n"
                    f"**Reporter ID:** {reporter_id}\n"
                    f"**Target ID:** {target_id}\n"
                    f"banned for {REPORTER_SPAM_BAN_DURATION} hours."
                ),
                color=0xFF0000,
                footer="made by unity.lolz"
            )
            redis.delete(spam_key)
            return jsonify({"status": "reporter_banned", "reason": "spam_reporting"}), 200

    if is_non_reportable(target_id):
        reporter_name = get_player_display_name(reporter_id)
        target_name   = get_player_display_name(target_id)
        if is_insta_banned(reporter_id):
            send_discord_webhook(
                WEBHOOK_SPECIAL,
                content=f"insta-ban user {reporter_name} (`{reporter_id}`) tried to report non-reportable {target_name} (`{target_id}`). room: {room_code}. no action taken."
            )
        else:
            ban_user_playfab(reporter_id, 1, f"reported a non-reportable ID ({target_id})")
            send_discord_webhook(
                WEBHOOK_HOST,
                title="tried to report staff",
                description=(
                    f"**Reporter:** {reporter_name}\n"
                    f"**Reporter ID:** {reporter_id}\n"
                    f"**Reported:** {target_name}\n"
                    f"**Reported ID:** {target_id}\n"
                    f"**Reason:** {reason}\n\n"
                    f"banned for 1 hour."
                ),
                color=0xFFA500,
                footer="made by unity.lolz"
            )
        return jsonify({"status": "reporter_banned", "reason": "non_reportable_target"}), 200

    reporter_name = get_player_display_name(reporter_id)
    target_name   = get_player_display_name(target_id)

    if is_trusted:
        embed_title = "tmod report"
        embed_color = 0xFF8C00
    elif is_host_flag:
        embed_title = "player banned"
        embed_color = 0xFF0000
    else:
        embed_title = "player reported"
        embed_color = 0x109999

    description = (
        f"**Reporter:** {reporter_name}\n"
        f"**Reporter ID:** {reporter_id}\n"
        f"**Reported:** {target_name}\n"
        f"**Reported ID:** {target_id}\n"
        f"**Reason:** {reason}"
    )

    main_webhook = WEBHOOK_TRUSTED if is_trusted else (WEBHOOK_HOST if is_host_flag else WEBHOOK_DEFAULT)
    send_discord_webhook(main_webhook, title=embed_title, description=description, color=embed_color, footer="made by unity.lolz")

    if is_host_flag and reporter_role in BAN_DURATIONS:
        ban_user_playfab(target_id, BAN_DURATIONS[reporter_role], f"banned by {reporter_role} ({reporter_name}): {reason}")

    if is_insta_banned(target_id):
        ban_user_playfab(target_id, 24, f"insta-ban triggered on {target_name}: {reason}")
        send_discord_webhook(
            WEBHOOK_SPECIAL,
            content=f"```insta-ban executed on {target_name} ({target_id})\nreported by {reporter_name} ({reporter_id})\nroom: {room_code}\nreason: {reason}```"
        )

    if reporter_role in ROLE_WEBHOOKS and not is_trusted:
        send_discord_webhook(
            ROLE_WEBHOOKS[reporter_role],
            title=f"{reporter_role} report",
            description=description + f"\n**Banned:** {'yes' if is_host_flag else 'no'}",
            color=0x808080,
            footer="made by unity.lolz"
        )

    return jsonify({"status": "ok"}), 200

# ── Staff routes ──────────────────────────────────────────────────────────────

@app.route("/staff/add", methods=["POST"])
def staff_add():
    data = request.get_json()
    playfab_id = data.get("playfab_id")
    role       = data.get("role")
    if not playfab_id or not role or role not in ALL_ROLES:
        return jsonify({"error": "missing or invalid fields"}), 400
    if redis.sismember(f"role:{role}", playfab_id):
        return jsonify({"status": "already_exists"}), 200
    redis.sadd(f"role:{role}", playfab_id)
    return jsonify({"status": "added"}), 200

@app.route("/staff/remove", methods=["POST"])
def staff_remove():
    data = request.get_json()
    playfab_id = data.get("playfab_id")
    role       = data.get("role")
    if not playfab_id or not role or role not in ALL_ROLES:
        return jsonify({"error": "missing or invalid fields"}), 400
    if not redis.sismember(f"role:{role}", playfab_id):
        return jsonify({"status": "not_found"}), 200
    redis.srem(f"role:{role}", playfab_id)
    return jsonify({"status": "removed"}), 200

@app.route("/staff/list", methods=["GET"])
def staff_list():
    role = request.args.get("role")
    if not role or role not in ALL_ROLES:
        return jsonify({"error": "invalid role"}), 400
    members = redis.smembers(f"role:{role}")
    return jsonify({"ids": list(members) if members else []}), 200

# ── Non-reportable routes ─────────────────────────────────────────────────────

@app.route("/nonreportable/add", methods=["POST"])
def nonreportable_add():
    data = request.get_json()
    playfab_id = data.get("playfab_id")
    if not playfab_id:
        return jsonify({"error": "missing playfab_id"}), 400
    if redis.sismember("non_reportable", playfab_id):
        return jsonify({"status": "already_exists"}), 200
    redis.sadd("non_reportable", playfab_id)
    return jsonify({"status": "added"}), 200

@app.route("/nonreportable/remove", methods=["POST"])
def nonreportable_remove():
    data = request.get_json()
    playfab_id = data.get("playfab_id")
    if not playfab_id:
        return jsonify({"error": "missing playfab_id"}), 400
    if not redis.sismember("non_reportable", playfab_id):
        return jsonify({"status": "not_found"}), 200
    redis.srem("non_reportable", playfab_id)
    return jsonify({"status": "removed"}), 200

@app.route("/nonreportable/list", methods=["GET"])
def nonreportable_list():
    members = redis.smembers("non_reportable")
    return jsonify({"ids": list(members) if members else []}), 200

# ── Insta-ban routes ──────────────────────────────────────────────────────────

@app.route("/instaban/add", methods=["POST"])
def add_insta_ban():
    data = request.get_json()
    playfab_id = data.get("playfab_id")
    if not playfab_id:
        return jsonify({"error": "missing playfab_id"}), 400
    redis.sadd("insta_bans", playfab_id)
    return jsonify({"status": "added"}), 200

@app.route("/instaban/remove", methods=["POST"])
def remove_insta_ban():
    data = request.get_json()
    playfab_id = data.get("playfab_id")
    if not playfab_id:
        return jsonify({"error": "missing playfab_id"}), 400
    redis.srem("insta_bans", playfab_id)
    return jsonify({"status": "removed"}), 200

@app.route("/instaban/list", methods=["GET"])
def list_insta_bans():
    members = redis.smembers("insta_bans")
    return jsonify({"insta_bans": list(members) if members else []}), 200

