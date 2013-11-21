"""Tests for the API autogeneration stuff."""

import yaml

from ocl import api
from ocl import data
from ocl import test
from ocl.service import glance


API_YAML = """
get_method:
  get:
    - [name, string]
  path: get_method
  response: $GetMethodResponse

get_method_without_query:
  get:
    - [image_id, custom_datatype_id]
  path: get_method_without_query
  response: $GetMethodWithoutQueryResponse
  request: $None

put_method:
  put:
    - [image_id, custom_datatype_id]
    - [can_share, boolean]
  path: put_method/%(image_id)s
  request: $PutMethodRequest
  response: $PutMethodResponse

post_method:
  post:
    - [image_id, custom_datatype_id]
    - [can_share, boolean]
  path: post_method
  request: $PostMethodRequest
  response: $PostMethodResponse
"""

GET_METHOD_RESPONSE = {
  'name': 'get_method',
  'type': 'object',
  'properties': {
    'get_method': {
      'type': 'object',
      'properties': {'name': {'type': 'string'}}
    }
  }
}

GET_METHOD_WITHOUT_QUERY_RESPONSE = {
  'name': 'get_method_without_query',
  'type': 'object',
  'properties': {
    'get_methods': {'type': 'array',
                    'items': GET_METHOD_RESPONSE}
    }
}

PUT_METHOD_REQUEST = {
  'name': 'put_method',
  'type': 'object',
  'properties': {
    'can_share': {'type': 'boolean'},
    }
  }

PUT_METHOD_RESPONSE = {
  'name': 'put_method',
  'type': 'object',
  'properties': {
    'put_method': PUT_METHOD_REQUEST,
    }
  }

POST_METHOD_REQUEST = {
  'name': 'post_method',
  'type': 'object',
  'properties': {
    'image_id': {'type': 'string'},
    'can_share': {'type': 'boolean'},
    }
  }

POST_METHOD_RESPONSE = {
  'name': 'post_method',
  'type': 'object',
  'properties': {
    'post_method': POST_METHOD_REQUEST,
    }
  }


models = {'GetMethodResponse': data.model_factory(GET_METHOD_RESPONSE),
          'GetMethodWithoutQueryResponse':
            data.model_factory(GET_METHOD_WITHOUT_QUERY_RESPONSE),
          'PutMethodRequest': data.request_factory(PUT_METHOD_REQUEST),
          'PutMethodResponse': data.model_factory(PUT_METHOD_RESPONSE),
          'PostMethodRequest': data.request_factory(POST_METHOD_REQUEST),
          'PostMethodResponse': data.model_factory(POST_METHOD_RESPONSE),
          }


class AutogenTests(test.TestCase):
  def test_glance_api_factory(self):
    GlanceAuto = api.api_factory('image', glance.glance_methods, glance.MODELS)
    self.assert_(hasattr(GlanceAuto, 'list_images'))

  def test_api_factory(self):
    api_methods = yaml.load(API_YAML)
    api_auto = api.api_factory('api', api_methods, models)
    self.assert_(hasattr(api_auto, 'get_method'))


class DataTests(test.TestCase):
  def test_request_factory(self):
    request = models['PostMethodRequest']({'image_id': '5a', 'can_share': True})
    self.assert_('post_method' in request)
    self.assertEquals(request['post_method']['image_id'], '5a')
    self.assertEquals(request['post_method']['can_share'], True)

  def test_response_factory(self):
    response = models['GetMethodResponse']({'get_method': {'name': 'foo'}})
    self.assert_('get_method' in response)
    self.assertEquals(response['get_method']['name'], 'foo')

  def test_bigger_response_factory(self):
    response = models['GetMethodWithoutQueryResponse'](
        {'get_methods': [{'get_method': {'name': 'foo'}},
                         {'get_method': {'name': 'bar'}}
                         ]
         })

    self.assert_('get_methods' in response)
    self.assert_('get_method' in response['get_methods'][0])
    self.assertEquals(response['get_methods'][0]['get_method']['name'], 'foo')
