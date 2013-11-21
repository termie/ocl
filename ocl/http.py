"""Little helpers for doing HTTP.

Somehow these get written every single time anybody writes anything.
"""

import functools
import json
import logging

import requests


class Replay(object):
  def __init__(self):
    self._original_request = requests.Session.request

  def _start_recording(self):
    @functools.wraps(requests.Session.request)
    def _wrapper(*args, **kw):
      kw.setdefault('hooks', {'response': [self._recording_hook]})
      return self._original_request(*args, **kw)

    requests.Session.request = _wrapper

  def _stop_recording(self):
    requests.Session.requests = self._original_request

  def _recording_hook(self, response):
    self.response = response


class Client(object):
  @staticmethod
  def post(url, data, headers=None, **kw):
    headers = headers and headers or {}
    headers.setdefault('Content-type', 'application/json')
    if type(data) == type({}):
      data = json.dumps(data)
    logging.debug('POST %s', url)
    for header in headers.iteritems():
      logging.debug('  %s', header)
    logging.debug('DATA')
    logging.debug(data)
    logging.debug('ENDDATA')
    rv = requests.post(url, data=data, headers=headers, **kw)
    return rv

  @staticmethod
  def put(url, data, headers=None, **kw):
    headers = headers and headers or {}
    headers.setdefault('Content-type', 'application/json')
    if type(data) == type({}):
      data = json.dumps(data)
    rv = requests.put(url, data=data, headers=headers, **kw)
    return rv

  @staticmethod
  def get(url, data, headers=None, **kw):
    headers = headers and headers or {}
    headers.setdefault('Content-type', 'application/json')

    logging.debug('GET %s', url)
    for header in headers.iteritems():
      logging.debug('  %s', header)
    logging.debug('DATA')
    logging.debug(data)
    logging.debug('ENDDATA')
    rv = requests.get(url, params=data, headers=headers, **kw)
    return rv

  @staticmethod
  def head(url, data, headers=None, **kw):
    headers = headers and headers or {}
    headers.setdefault('Content-type', 'application/json')
    rv = requests.head(url, params=data, headers=headers, **kw)
    return rv

  @staticmethod
  def delete(url, data, headers=None, **kw):
    headers = headers and headers or {}
    headers.setdefault('Content-type', 'application/json')
    rv = requests.delete(url, params=data, headers=headers, **kw)
    return rv

  @staticmethod
  def options(url, data, headers=None, **kw):
    headers = headers and headers or {}
    headers.setdefault('Content-type', 'application/json')
    rv = requests.options(url, params=data, headers=headers, **kw)
    return rv


client = Client()
