import yaml

from ocl import api
from ocl import cache
from ocl import data
from ocl import plugin
# TODO(termie): being lazy
from ocl.http import client as http

property_meta_prefix = 'x-image-meta-property-'
meta_prefix = 'x-image-meta-'


def collapse_meta_headers(headers):
  o = {'properties': {}}
  for k, v in headers.iteritems():
    if k.startswith(property_meta_prefix):
      o['properties'][k[len(property_meta_prefix):]] = v
    elif k.startswith(meta_prefix):
      o[k[len(meta_prefix):]] = v
  return o


def expand_meta_headers(meta):
  o = {}
  for k, v in meta.iteritems():
    if k == 'properties':
      for pk, pv in v.iteritems():
        o['%s%s' % (property_meta_prefix, pk)] = pv
    else:
      o['%s%s' % (meta_prefix, k)] = v
  return o


IMAGE_SCHEMA_V1 = {'name': 'image',
                   'type': 'object',
                   'properties': {
                      'checksum': {'type': 'string'},
                      'container_format': {'type': 'string'},
                      'disk_format': {'type': 'string'},
                      'id': {'type': 'string'},
                      'name': {'type': 'string'},
                      'size': {'type': 'integer'}
                      }
                   }


IMAGES_SCHEMA_V1 = {'name': 'images',
                    'type': 'object',
                    'properties': {
                      'images': {'type': 'array',
                                 'items': IMAGE_SCHEMA_V1}
                      }
                    }


IMAGE_SCHEMA_YAML = """
image_schema: &image_schema
  name: images
  type: object
  properties:
    images: {type: string}
    checksum: {type: string}

image_response: &image_response
  name: image_response
  type: object
  properties:
    image: *image_schema

"""

Image = data.model_factory(IMAGE_SCHEMA_V1)
Images = data.model_factory(IMAGES_SCHEMA_V1)


class Glance(api.Base):
  catalog_type = 'image'

  # TODO(termie): fill in the rest of the filters
  def list_images(self, name=None, auth_ref=None, cache_ref=None):
    endpoint = 'images'
    qs = {}
    qs['name'] = name
    qs = dict((k, v) for k, v in qs.iteritems() if v is not None)

    replay = http.Replay()
    replay._start_recording()
    rv = self._get(endpoint, data=qs, auth_ref=auth_ref)
    replay._stop_recording()
    print replay.response
    images = rv.json()
    if cache_ref:
      for image in images['images']:
        cache_ref.image_id(image['name'], image['id'])

    return Images(images)

  # TODO(termie): fill in the rest of the filters
  def list_images_detail(self, auth_ref=None, cache_ref=None):
    endpoint = 'images/detail'

    rv = self._get(endpoint, auth_ref=auth_ref)
    images = rv.json()
    if cache_ref:
      for image in images['images']:
        cache_ref.image_id(image['name'], image['id'])

    return image

  @cache.readthrough('image_id', 'image_name')
  def image_id(self, image_name, auth_ref=None, cache_ref=None):
    images = self.list_images(
        name=image_name, auth_ref=auth_ref, cache_ref=cache_ref)
    for image in images['images']:
      if image['name'] == image_name:
        return image['id']
    raise Exception('not found')

  @cache.replace('image_id', 'image_id')
  def meta(self, image_id, auth_ref=None, cache_ref=None):
    endpoint = 'images/%s' % image_id
    rv = self._head(endpoint, auth_ref=auth_ref)
    # TODO(termie): turn timestamps into datetime.datetimes
    return collapse_meta_headers(rv.headers)

  @cache.replace('image_id', 'image_id')
  def list_members(self, image_id, auth_ref=None, cache_ref=None):
    endpoint = 'images/%s/members' % image_id
    rv = self._get(endpoint, auth_ref=auth_ref)
    return rv.json()

  @cache.replace('tenant_name', 'tenant_name')
  def list_shared(self, tenant_name, auth_ref=None, cache_ref=None):
    endpoint = 'shared-images/%s' % tenant_name
    rv = self._get(endpoint, auth_ref=auth_ref)
    return rv.json()

  @cache.replace('image_id', 'image_id')
  @cache.replace('tenant_name', 'tenant_name')
  def add_member(self, image_id, tenant_name, can_share=None, auth_ref=None,
                 cache_ref=None):
    endpoint = 'images/%s/members/%s' % (image_id, tenant_name)
    data = {}
    if can_share is not None:
      data = {'member': {'can_share': can_share}}
    rv = self._put(endpoint, data=data, auth_ref=auth_ref)
    return rv.json()

  @cache.replace('image_id', 'image_id')
  @cache.replace('tenant_name', 'tenant_name')
  def remove_member(self, image_id, tenant_name, auth_ref=None, cache_ref=None):
    endpoint = 'images/%s/members/%s' % (image_id, tenant_name)
    rv = self._delete(endpoint, auth_ref=auth_ref)
    return rv.json()

  @cache.replace('image_id', 'image_id')
  def replace_members(self, image_id, members, auth_ref=None, cache_ref=None):
    endpoint = 'images/%s/members' % image_id

    # members looks like {'member_id': tenant_id, 'can_share': false}
    data = {'memberships': members}
    rv = self._put(endpoint, data=data, auth_ref=auth_ref)
    return rv



ADD_MEMBER_REQUEST_SCHEMA = {
  'name': 'members',
  'type': 'object',
  'properties': {
    'can_share': {'type': 'boolean'},
    }
  }

ADD_MEMBER_REQUEST_YAML = """
  name: members
  type: object
  propertes:
    - can_share: {'type': 'boolean'}

"""


GLANCE_YAML = """
  list_images:
    get:
      - [name, string]
    path: images
    response: $ImagesResponse

  list_members:
    get:
      - [image_id, image_id]
    path: images/%(image_id)s/members
    request: $None

  add_member:
    put:
      - [image_id, image_id]
      - [tenant_name, tenant_name]
      - [can_share, boolean]
    path: images/%(image_id)s/members
    request: $AddMemberRequest
    # response: $MemberResponse
"""


MODELS = {'ImageResponse': data.model_factory(IMAGE_SCHEMA_V1),
          'ImagesResponse': data.model_factory(IMAGES_SCHEMA_V1),
          'AddMemberRequest': data.request_factory(ADD_MEMBER_REQUEST_SCHEMA),
          'AddMemberRequest': data.request_factory(yaml.load(ADD_MEMBER_REQUEST_YAML)),
          }


glance_methods = yaml.load(GLANCE_YAML)
GlanceAuto = api.api_factory('image', glance_methods, MODELS)


def register():
  plugin.lazy_api('glance', Glance())
  plugin.lazy_api('glance_auto', GlanceAuto())
