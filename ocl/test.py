import cStringIO as StringIO
import json
import unittest

import mock
import requests
from requests import structures

from ocl import auth


def load_flow(name):
  flow = json.load(open('tests/flows/%s.json' % name))
  return flow


class TestCase(unittest.TestCase):
  def assertDictShape(self, actual, expected):
    for k, v in expected.iteritems():
      if k not in actual:
        raise AssertionError('%s not present in dict %s' % (k, actual))
      if type(v) == type({}):
        self.assertDictShape(actual[k], expected[k])


def fake_response(res):
  response = requests.Response()
  response.raw = StringIO.StringIO(res['content'])
  response.headers = structures.CaseInsensitiveDict(res['headers'])
  response.status_code = res['code']
  #response.url = '%s://%s:%s%s' % (res['scheme'], res['host'], res['port'], res['path'])
  return response


class Flow(TestCase):
  def __init__(self, flow):
    self.flow = load_flow(flow)
    self.index = 0
    self._patches = []

  def __enter__(self):
    self._patches.append(mock.patch('requests.get', self.get))
    self._patches.append(mock.patch('requests.post', self.post))
    self._patches.append(mock.patch('requests.put', self.put))
    self._patches.append(mock.patch('requests.head', self.head))
    self._patches.append(mock.patch('requests.delete', self.delete))
    for patcher in self._patches:
      patcher.start()
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    for patcher in self._patches:
      patcher.stop()
    self.assert_(self.index == len(self.flow), 'did not reach end of flow')

  def _do_request(self, method, url, data=None, params=None, headers=None):
    req = self.flow[self.index]['request']
    res = self.flow[self.index]['response']
    self.assertEquals(method, req['method'])

    if method in ('POST', 'PUT'):
      actual = json.loads(data)
      expected = json.loads(req['content'])
      self.assertDictShape(actual, expected)
    else:
      expected = req['query']
      actual = params
      for k, v in expected:
        self.assertIn(k, actual)

    self.index += 1
    return fake_response(res)

  def get(self, url, data=None, params=None, headers=None):
    return self._do_request('GET', url, params=params, headers=headers)

  def post(self, url, data=None, params=None, headers=None):
    return self._do_request('POST', url, data=data, headers=headers)

  def put(self, url, data=None, params=None, headers=None):
    return self._do_request('PUT', url, data=data, headers=headers)

  def head(self, url, data=None, params=None, headers=None):
    return self._do_request('HEAD', url, params=params, headers=headers)

  def delete(self, url, data=None, params=None, headers=None):
    return self._do_request('delete', url, params=params, headers=headers)


class ApiTestCase(TestCase):
  def authenticate(self, auth_url='http://foo/', user='foo', password='foo',
                   tenant='foo'):
    return auth.authenticate(
        auth_url=auth_url, user=user, password=password, tenant=tenant)
