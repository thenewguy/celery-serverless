# coding: utf-8
try:  # https://github.com/UnitedIncome/serverless-python-requirements#dealing-with-lambdas-size-limitations
    import unzip_requirements
except ImportError:
    pass

import os
import json
import logging

from celery_serverless.handler_utils import handler_wrapper

logger = logging.getLogger(__name__)
logger.propagate = True
if os.environ.get('CELERY_SERVERLESS_LOGLEVEL'):
    logger.setLevel(os.environ.get('CELERY_SERVERLESS_LOGLEVEL'))
print('Celery serverless loglevel:', logger.getEffectiveLevel())

from redlock import RedLock
from celery_serverless.watchdog import Watchdog
from celery_serverless.worker_management import spawn_worker, attach_hooks
hooks = []


@handler_wrapper
def worker(event, context):
    global hooks

    try:
        remaining_seconds = context.get_remaining_time_in_millis() / 1000.0
    except Exception as e:
        logger.exception('Could not got remaining_seconds. Is the context right?')
        remaining_seconds = 5 * 60 # 5 minutes by default

    softlimit = remaining_seconds-30.0  # Poke the job 30sec before the abyss
    hardlimit = remaining_seconds-15.0  # Kill the job 15sec before the abyss

    if not hooks:
        logger.debug('Fresh Celery worker. Attach hooks!')
        hooks = attach_hooks()
    else:
        logger.debug('Old Celery worker. Already have hooks.')

    # The Celery worker will start here. Will connect, take 1 (one) task,
    # process it, and quit.
    logger.debug('Spawning the worker(s)')
    spawn_worker(
        softlimit=softlimit if softlimit > 5 else None,
        hardlimit=hardlimit if hardlimit > 5 else None,
        loglevel='DEBUG',
    )  # Will block until one task got processed

    logger.debug('Cleaning up before exit')
    body = {
        "message": "Celery worker worked, lived, and died.",
    }
    return {"statusCode": 200, "body": json.dumps(body)}


@handler_wrapper
def watchdog(event, context):
    lock_name = os.environ.get('CELERY_SERVERLESS_LOCK_NAME', 'celery_serverless')
    lock_url = os.environ.get('CELERY_SERVERLESS_LOCK_URL')
    assert lock_url, 'The CELERY_SERVERLESS_LOCK_URL envvar should be set. Even to "disabled" to disable it.'

    queue_url = os.environ.get('CELERY_SERVERLESS_QUEUE_URL')
    assert queue_url, 'The CELERY_SERVERLESS_QUEUE_URL envvar should be set. Even to "disabled" to disable it.'

    if lock_url == 'disabled':
        lock = None
        cache = None
    elif lock_url.startswith(('redis://', 'rediss://')):
        lock = RedLock(lock_name, connection_details=[{'url': node} for node in lock_url.split(',')])
        cache = lock.redis_nodes[0]  # Using the Lock redis as values cache
    else:
        raise RuntimeWarning("This URL is not supported. Only 'redis[s]://...' is supported for now")

    if queue_url == 'disabled':
        watched = None
    elif queue_url.startswith('amqp://'):
        raise NotImplementedError('Should create an object to be watched')
    else:
        raise RuntimeWarning("This URL is not supported. Only 'amqp://...' is supported for now")

    Watchdog(cache=cache, name=lock_name, lock=lock, watched=watched).monitor()

    logger.debug('Cleaning up before exit')
    body = {
        "message": "Watchdog woke, worked, and rested.",
    }
    return {"statusCode": 200, "body": json.dumps(body)}
