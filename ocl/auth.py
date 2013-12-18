from ocl.service import keystone


class Auth(object):
  """Store credentials."""
  def __init__(self, token, user, tenant, catalog):
    self.token = token
    self.user = user
    self.tenant = tenant
    # NOTE(termie): Technically this is returned as a list, but I think we
    #               should be accessing it as a dict
    self.raw_catalog = catalog
    self.catalog = {}
    for x in catalog:
      self.catalog[x['type']] = _ServiceCollection(type=x['type'],
                                                   name=x['name'],
                                                   endpoints=x['endpoints'])

  @property
  def token_id(self):
    return self.token['id']

  @classmethod
  def from_authenticate(cls, auth_resp):
    return cls(token=auth_resp['access']['token'],
               user=auth_resp['access']['user'],
               tenant=auth_resp['access']['token']['tenant'],
               catalog=auth_resp['access']['serviceCatalog'])


class _ServiceCollection(object):
  """By default use the first provided endpoint but allow deeper access."""
  def __init__(self, type, name, endpoints, index=0):
    self.type = type
    self.name = name

    self.endpoints = []
    for e in endpoints:
      trans = {'name': self.name,
               'type': self.type,
               'region': e.get('region', ''),
               'public_url': e.get('publicURL', ''),
               'internal_url': e.get('internalURL', ''),
               'admin_url': e.get('adminURL', ''),
               }
      self.endpoints.append(_ServiceData(**trans))
    self.index = index

  def __getattr__(self, key):
    return getattr(self.endpoints[self.index], key)

  def __getitem__(self, index):
    return self.endpoints[index]

  def to_dict(self):
    return {'type': self.type,
            'name': self.name,
            'endpoints': [x.to_dict() for x in self.endpoints]}


class _Data(object):
  def __init__(self, **kw):
    for k, v in kw.iteritems():
      setattr(self, k, v)
    self._data = kw

  def to_dict(self):
    return self._data


class _ServiceData(_Data):
  pass


def authenticate(auth_url, user, password, tenant):
  """Shortcut for authenticating."""
  ks_client = keystone.Keystone()

  token = ks_client.authenticate(user=user,
                                 password=password,
                                 tenant=tenant,
                                 auth_url=auth_url)

  auth_ref = Auth.from_authenticate(token)
  return auth_ref
