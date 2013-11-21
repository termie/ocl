from ocl import api
from ocl import cache
from ocl import plugin
from ocl.http import client as http


class Keystone(api.Base):
  catalog_type = 'identity'

  def authenticate(self, user, password, tenant, auth_url=None, auth_ref=None):
    if auth_ref and not auth_url:
      auth_url = self.public_url(auth_ref=auth_ref)
    data = {'auth': {
              'passwordCredentials': {
                'username': user,
                'password': password,
                },
              'tenantName': tenant,
              }
            }
    url = '%s/%s' % (auth_url, 'tokens')
    rv = http.post(url, data=data)
    return rv.json()

  def _post_admin(self, *args, **kw):
    kw.setdefault('base_url', self.admin_url(kw.get('auth_ref')))
    return self._post(*args, **kw)

  def _put_admin(self, *args, **kw):
    kw.setdefault('base_url', self.admin_url(kw.get('auth_ref')))
    return self._put(*args, **kw)

  def _get_admin(self, *args, **kw):
    kw.setdefault('base_url', self.admin_url(kw.get('auth_ref')))
    return self._get(*args, **kw)

  def _head_admin(self, *args, **kw):
    kw.setdefault('base_url', self.admin_url(kw.get('auth_ref')))
    return self._head(*args, **kw)

  def _delete_admin(self, *args, **kw):
    kw.setdefault('base_url', self.admin_url(kw.get('auth_ref')))
    return self._delete(*args, **kw)

  def _options_admin(self, *args, **kw):
    kw.setdefault('base_url', self.admin_url(kw.get('auth_ref')))
    return self._options(*args, **kw)

  def extensions(self, auth_ref=None, cache_ref=None):
    endpoint = 'extensions'
    rv = self._get(endpoint, auth_ref=auth_ref)
    return rv.json()

  def list_tenants(self, auth_ref=None, cache_ref=None):
    endpoint = 'tenants'
    rv = self._get(endpoint, auth_ref=auth_ref)
    all_tenants = rv.json()
    if cache_ref:
      for t in all_tenants['tenants']:
        cache_ref.tenant_id(t['name'], t['id'])
        cache_ref.tenant_name(t['id'], t['name'])
    return all_tenants

  def token_get(self, token, auth_ref=None, cache_ref=None):
    endpoint = 'tokens/%s' % token
    rv = self._get(endpoint, auth_ref=auth_ref)
    #print rv.json()
    return rv.json()

  def list_tenants_admin(self, auth_ref=None, cache_ref=None):
    endpoint = 'tenants'
    rv = self._get_admin(endpoint, auth_ref=auth_ref)
    # Cache the id / name lookups
    all_tenants = rv.json()
    if cache_ref:
      for t in all_tenants['tenants']:
        cache_ref.tenant_id(t['name'], t['id'])
        cache_ref.tenant_name(t['id'], t['name'])
    return all_tenants

  @cache.replace('tenant_id', 'tenant_id')
  def get_tenant(self, tenant_id, auth_ref=None, cache_ref=None):
    endpoint = 'tenants/%s' % tenant_id
    rv = self._get_admin(endpoint, auth_ref=auth_ref)
    tenant = rv.json()
    t = tenant['tenant']
    if cache_ref:
      cache_ref.tenant_id(t['name'], t['id'])
      cache_ref.tenant_name(t['id'], t['name'])
    return tenant

  @cache.readthrough('tenant_id', 'tenant_name')
  def tenant_id(self, tenant_name, auth_ref=None, cache_ref=None):
    """Get the tenant id given a tenant name."""
    all_tenants = self.list_tenants_admin(auth_ref=auth_ref)
    for t in all_tenants['tenants']:
      if t['name'].lower() == tenant_name.lower():
        return t['id']
    raise Exception('not found')

  @cache.readthrough('tenant_name', 'tenant_id')
  def tenant_name(self, tenant_id, auth_ref=None, cache_ref=None):
    """Get the tenant name for a tenant id."""
    tenant = self.get_tenant(tenant_id, auth_ref=auth_ref)
    return tenant['tenant']['name']


class CatalogApi(api.Base):
  def _url(self, which, type, region=None, auth_ref=None):
    if region is None:
      return getattr(auth_ref.catalog[type], '%s_url' % which)
    else:
      for x in auth_ref.catalog[type]:
        if x.region == region:
          return getattr(x, '%s_url' % which)

  def info(self, type, auth_ref=None, cache_ref=None):
    return auth_ref.catalog[type].to_dict()

  def list(self, auth_ref=None, cache_ref=None):
    return dict((k, v.to_dict()) for k, v in auth_ref.catalog.iteritems())

  def public_url(self, type, region=None, auth_ref=None, cache_ref=None):
    return self._url('public', type, region=region, auth_ref=auth_ref)

  def internal_url(self, type, region=None, auth_ref=None, cache_ref=None):
    return self._url('internal', type, region=region, auth_ref=auth_ref)

  def admin_url(self, type, region=None, auth_ref=None, cache_ref=None):
    return self._url('admin', type, region=region, auth_ref=auth_ref)


def register():
  plugin.lazy_api('catalog', CatalogApi())
  plugin.lazy_api('keystone', Keystone())
