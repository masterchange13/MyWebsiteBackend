import time

from django.core.cache import cache

ONLINE_USERS_KEY = "chat:presence:online_users"
CONNECTIONS_KEY_PREFIX = "chat:presence:connections:"
ONLINE_TTL_SECONDS = 90


def get_redis():
    return cache.client.get_client(write=True)


def _connections_key(username: str) -> str:
    return f"{CONNECTIONS_KEY_PREFIX}{username}"


def _now_ts() -> int:
    return int(time.time())


def _decode_members(members) -> set[str]:
    return {
        member.decode("utf-8") if isinstance(member, bytes) else str(member)
        for member in members or []
    }


def touch_user(username: str):
    if not username:
        return
    try:
        get_redis().zadd(ONLINE_USERS_KEY, {username: _now_ts()})
    except Exception:
        pass


def mark_login(username: str):
    touch_user(username)


def mark_logout(username: str):
    if not username:
        return
    try:
        redis_client = get_redis()
        redis_client.zrem(ONLINE_USERS_KEY, username)
        redis_client.delete(_connections_key(username))
    except Exception:
        pass


def mark_connection_online(username: str, connection_id: str):
    if not username:
        return
    try:
        redis_client = get_redis()
        redis_client.sadd(_connections_key(username), connection_id)
        redis_client.expire(_connections_key(username), ONLINE_TTL_SECONDS * 2)
        touch_user(username)
    except Exception:
        pass


def refresh_connection(username: str, connection_id: str):
    if not username:
        return
    try:
        redis_client = get_redis()
        redis_client.sadd(_connections_key(username), connection_id)
        redis_client.expire(_connections_key(username), ONLINE_TTL_SECONDS * 2)
        touch_user(username)
    except Exception:
        pass


def mark_connection_offline(username: str, connection_id: str):
    if not username:
        return False
    try:
        redis_client = get_redis()
        connections_key = _connections_key(username)
        if connection_id:
            redis_client.srem(connections_key, connection_id)
        if redis_client.scard(connections_key) > 0:
            redis_client.expire(connections_key, ONLINE_TTL_SECONDS * 2)
            touch_user(username)
            return True
        redis_client.delete(connections_key)
        redis_client.zrem(ONLINE_USERS_KEY, username)
        return False
    except Exception:
        return False


def get_online_usernames() -> set[str]:
    try:
        redis_client = get_redis()
        cutoff = _now_ts() - ONLINE_TTL_SECONDS
        redis_client.zremrangebyscore(ONLINE_USERS_KEY, "-inf", cutoff - 1)
        members = redis_client.zrangebyscore(ONLINE_USERS_KEY, cutoff, "+inf")
        return _decode_members(members)
    except Exception:
        return set()
