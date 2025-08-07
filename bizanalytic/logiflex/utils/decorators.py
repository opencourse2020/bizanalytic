# decorators.py

import logging
import time
from threading import Lock

from ratelimit import limits, sleep_and_retry
from retry import retry

RATE_LIMIT = 2000


def log_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}")
            return [], []

    return wrapper


def print_progress(func):
    def wrapper(*args, **kwargs):
        total = kwargs.get('total', 1)
        result = None
        for i in range(total):
            result = func(*args, **kwargs)
            progress = int((i + 1) / total * 10)
            print(f"Registering faces: {'😀' * progress}{'😐' * (10 - progress)} {i + 1}/{total}")
            time.sleep(1)
        return result

    return wrapper


@sleep_and_retry
@limits(calls=RATE_LIMIT, period=60)
def rate_limited_call(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


@retry(tries=3, delay=2, backoff=2)
def retry_call(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


class TokenBucket:
    def __init__(self, rate, capacity):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.lock = Lock()
        self.last_refill = time.time()

    def consume(self, tokens):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


def token_bucket(rate, capacity):
    bucket = TokenBucket(rate, capacity)

    def decorator(func):
        def wrapper(*args, **kwargs):
            if bucket.consume(1):
                return func(*args, **kwargs)
            else:
                logging.warning("Token bucket limit reached. Try again later.")
                return None

        return wrapper

    return decorator