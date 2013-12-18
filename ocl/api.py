import functools
import sys

import pkg_resources

from ocl.http import client as http


CLEANERS = {'default': lambda x: x}

MODELS = {'None': lambda x: None}


class Api(object):
  """API generated based on the plugin system."""
  _REGISTRY = {}

  def __init__(self, *args, **kw):
    super(Api, self).__init__(*args, **kw)

    for ep in pkg_resources.iter_entry_points(group='ocl.api.plugins'):
      registration_func = ep.load()
      registration_func()

    # Do the main classes first
    for x in self._REGISTRY:
      if '.' in x:
        continue

      setattr(self, x, self._REGISTRY[x])

    # Then overrides and additions
    for x in self._REGISTRY:
      if '.' not in x:
        continue
      base, method = x.split('.')

      setattr(getattr(self, base), method, self._REGISTRY[x])


def request(method, url, data=None, headers=None, auth_ref=None):
  headers = headers and headers or {}
  if auth_ref:
    headers['X-Auth-Token'] = auth_ref.token_id
  f = getattr(http, method)
  rv = f(url, data, headers=headers)
  return rv


def get(url, data=None, headers=None, auth_ref=None):
  return request('get', url, data=data, headers=headers, auth_ref=auth_ref)


def post(url, data=None, headers=None, auth_ref=None):
  return request('post', url, data=data, headers=headers, auth_ref=auth_ref)


def put(url, data=None, headers=None, auth_ref=None):
  return request('put', url, data=data, headers=headers, auth_ref=auth_ref)


def options(url, data=None, headers=None, auth_ref=None):
  return request('options', url, data=data, headers=headers, auth_ref=auth_ref)


def delete(url, data=None, headers=None, auth_ref=None):
  return request('delete', url, data=data, headers=headers, auth_ref=auth_ref)


def head(url, data=None, headers=None, auth_ref=None):
  return request('head', url, data=data, headers=headers, auth_ref=auth_ref)


class Base(object):
  catalog_type = None
  requests_config = {'danger_mode': False,
                     'verbose': sys.stderr}

  def public_url(self, auth_ref):
    """Get our public url from the catalog."""
    return auth_ref.catalog[self.catalog_type].public_url

  def admin_url(self, auth_ref, cache_ref=None):
    """Get our admin url from the catalog."""
    return auth_ref.catalog[self.catalog_type].admin_url

  # http stuff
  def _url(self, endpoint=None, base_url=None, auth_ref=None):
    """Helper to build up public urls."""
    url = base_url
    if not url:
      url = self.public_url(auth_ref)

    if endpoint:
      url = '%s/%s' % (url, endpoint)

    return url

  def _post(self, endpoint, data=None, headers=None, base_url=None,
            auth_ref=None):
    url = self._url(endpoint, base_url=base_url, auth_ref=auth_ref)
    rv = post(url, data=data, headers=headers, auth_ref=auth_ref)
    return self._check_errors(rv)

  def _put(self, endpoint, data=None, headers=None, base_url=None,
           auth_ref=None):
    url = self._url(endpoint, base_url=base_url, auth_ref=auth_ref)
    rv = put(url, data=data, headers=headers, auth_ref=auth_ref)
    return self._check_errors(rv)

  def _get(self, endpoint, data=None, headers=None, base_url=None,
           auth_ref=None):
    url = self._url(endpoint, base_url=base_url, auth_ref=auth_ref)
    rv = get(url, data=data, headers=headers, auth_ref=auth_ref)
    return self._check_errors(rv)

  def _head(self, endpoint, data=None, headers=None, base_url=None,
            auth_ref=None):
    url = self._url(endpoint, base_url=base_url, auth_ref=auth_ref)
    rv = head(url, data=data, headers=headers, auth_ref=auth_ref)
    return self._check_errors(rv)

  def _delete(self, endpoint, data=None, headers=None, base_url=None,
              auth_ref=None):
    url = self._url(endpoint, base_url=base_url, auth_ref=auth_ref)
    rv = delete(url, data=data, headers=headers, auth_ref=auth_ref)
    return self._check_errors(rv)

  def _options(self, endpoint, data=None, headers=None, base_url=None,
               auth_ref=None):
    url = self._url(endpoint, base_url=base_url, auth_ref=auth_ref)
    rv = options(url, data=data, headers=headers, auth_ref=auth_ref)
    return self._check_errors(rv)

  # error handling
  def _check_errors(self, rv):
    """Cascade through possible error handlers."""
    if rv.status_code < 300 and rv.status_code >= 200:
      return rv
    default = self._handle_http_error
    broad = getattr(self, '_handle_http_%sxx' % str(rv.status_code)[0], default)
    handler = getattr(self, '_handle_%s' % rv.status_code, broad)
    return handler(rv)

  def _handle_http_error(self, rv):
    print >> sys.stderr, 'OH SHIT SON, WE GOT AN ERROR'
    print rv.text
    rv.raise_for_status()
    return rv


class ApiMethod(object):
  _request_factory = staticmethod(lambda x: x)
  _response_factory = staticmethod(lambda x: x)

  def __init__(self, method_def, models, cleaners):
    self._load_from_def(method_def, models, cleaners)

  def _models(self, models):
    _m = MODELS.copy()
    _m.update(models)
    return _m

  def _cleaners(self, cleaners):
    _m = CLEANERS.copy()
    _m.update(cleaners)
    return _m

  def _load_from_def(self, method_def, models, cleaners):
    models = self._models(models)
    cleaners = self._cleaners(cleaners)
    self._path = method_def['path']

    args = None
    http_method = None
    for _http_method in ('get', 'post', 'put', 'head', 'delete'):
      if _http_method in method_def:
        args = method_def[_http_method]
        http_method = _http_method
        break

    self._call = getattr(self, '_do_%s' % http_method)

    self._args = {}
    self._ordered_args = []
    for key, cleaner in args:
      self._ordered_args.append(key)
      self._args[key] = cleaners.get(cleaner, cleaners['default'])

    request_def = method_def.get('request')
    if request_def:
      # Naively assume that we are using the standard markup of $ModelName
      self._request_factory = models[request_def[1:]]

    response_def = method_def.get('response')
    if response_def:
      # Naively assume that we are using the standard markup of $ModelName
      self._response_factory = models[response_def[1:]]

  def _build_request(self, params, kw):
    return self._request_factory(params)

  def _build_response(self, rv, kw):
    return self._response_factory(rv.json())

  def _clean_args(self, args, kw):
    # If we got passed positionals, turn them into keyword args
    for i, value in enumerate(args):
      kw[self._ordered_args[i]] = value

    params = {}
    for k, cleaner in self._args.iteritems():
      params[k] = cleaner(kw.get(k, None))
    params = dict((k, v) for k, v in params.iteritems() if v)
    return params

  def _do_get(self, instance, *args, **kw):
    return self._do(instance._get, *args, **kw)

  def _do_put(self, instance, *args, **kw):
    return self._do(instance._put, *args, **kw)

  def _do_post(self, instance, *args, **kw):
    return self._do(instance._put, *args, **kw)

  def _do_delete(self, instance, *args, **kw):
    return self._do(instance._delete, *args, **kw)

  def _do(self, method, *args, **kw):
    params = self._clean_args(args, kw)
    data = self._build_request(params, kw)
    rv = method(self._path % params, data, auth_ref=kw.get('auth_ref'))
    response = self._build_response(rv, kw)
    return response

  def __call__(self, *args, **kw):
    return self._call(self._instance, *args, **kw)

  def __get__(self, instance, owner):
    self._instance = instance
    return self


def api_factory(name, methods, models, cleaners=CLEANERS):
  class _Api(Base):
    catalog_type = name

  for method, method_def in methods.iteritems():
    setattr(_Api, method, ApiMethod(method_def, models, cleaners))

  return _Api


def full_auto(path):
  """Given the path to a YAML file, attempt to generate a full API."""
  pass

# TODO(termie): these could probably be refactored into one base class
class Authenticated(object):
  def __init__(self, wrapped, auth_ref):
    self.wrapped = wrapped
    self.auth_ref = auth_ref

  def _wrap_method(self, f):
    @functools.wraps(f)
    def _wrapped(*args, **kw):
      kw.setdefault('auth_ref', self.auth_ref)
      return f(*args, **kw)
    return _wrapped

  def _wrap_instance(self, i):
    return self.__class__(i, self.auth_ref)

  def __getattr__(self, name):
    attr = getattr(self.wrapped, name)
    if isinstance(attr, Base):
      return self._wrap_instance(attr)
    if not callable(attr):
      return attr
    if name[0] == '_':
      return attr

    wrap = self._wrap_method(attr)
    setattr(self, name, wrap)
    return wrap


class Cached(object):
  def __init__(self, wrapped, cache_ref):
    self.wrapped = wrapped
    self.cache_ref = cache_ref

  def _wrap_method(self, f):
    @functools.wraps(f)
    def _wrapped(*args, **kw):
      kw.setdefault('cache_ref', self.cache_ref)
      return f(*args, **kw)
    return _wrapped

  def _wrap_instance(self, i):
    return self.__class__(i, self.cache_ref)

  def __getattr__(self, name):
    attr = getattr(self.wrapped, name)
    if isinstance(attr, Base):
      return self._wrap_instance(attr)
    if not callable(attr):
      return attr
    if name[0] == '_':
      return attr

    wrap = self._wrap_method(attr)
    setattr(self, name, wrap)
    return wrap


