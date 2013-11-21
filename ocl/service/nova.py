import os

import yaml

from ocl import api
from ocl import cache
from ocl import plugin


class Nova(api.Base):
  catalog_type = 'compute'

  #@cache.replace('tenant_id', 'tenant_id')
  @cache.replace('image_id', 'image_id')
  @cache.replace('flavor_id', 'flavor_id')
  def boot(self, image_id, flavor_id, name=None, lookup=False,
           auth_ref=None, cache_ref=None):
    if name is None:
       name = 'foo'

    endpoint = 'servers'
    data = {'server': {
              'flavorRef': flavor_id,
              'imageRef': image_id,
              'name': name}}
    rv = self._post(endpoint, data=data, auth_ref=auth_ref)
    return rv.json()


  def list_flavors(self, auth_ref=None, cache_ref=None):
    endpoint = 'flavors'
    rv = self._get(endpoint, auth_ref=auth_ref)
    flavors = rv.json()
    if cache_ref:
      for flavor in flavors['flavors']:
        cache_ref.flavor_id(flavor['name'], flavor['id'])
    return flavors

  @cache.readthrough('flavor_id', 'flavor_name')
  def flavor_id(self, flavor_name, auth_ref=None, cache_ref=None):
    flavors = self.list_flavors(auth_ref=auth_ref, cache_ref=cache_ref)
    for flavor in flavors['flavors']:
      if flavor['name'] == flavor_name:
        return flavor['id']
    raise Exception('not found')


nova_yaml = open(os.path.join(os.path.dirname(__file__), 'nova.yaml')).read()
nova_methods = yaml.load(nova_yaml)
NovaAuto = api.api_factory('compute', nova_methods, {})


def register():
  plugin.lazy_api('nova', Nova())
  plugin.lazy_api('nova_auto', NovaAuto())
