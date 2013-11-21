import functools
import inspect
import json

import requests


UNSET = (None, None)


def evil_wraps(fn):
  """Decorator helper that makes `wrapped` have the same sig as `fn`.

  This is a bit of an evil hack and is only really necessary when using
  the autogenerating introspecting API.

  Used the same way as functools.wraps, just with more oomph.
  """
  def _wrapper(wrapped):
    argspec = inspect.getargspec(fn)
    formatted_args = inspect.formatargspec(*argspec)
    call_args = ['%s=%s' % (x, x) for x in argspec[0]]
    formatted_call_args = '(%s)' % ', '.join(call_args)
    fndef = 'lambda %s: _wrapped%s' % (
      formatted_args.lstrip('(').rstrip(')'), formatted_call_args)

    fake_fn = eval(fndef, {'_wrapped': wrapped})
    return functools.wraps(fn)(fake_fn)

  return _wrapper


def _arg_pos(f, arg_name):
  """Find the position of a positional arg."""
  f_args, f_varargs, f_keywords, f_defaults = inspect.getargspec(f)
  arg_pos = f_args.index(arg_name)
  return arg_pos


def replace(target, var):
  """Possibly replace the value of an argument with the cache lookup."""
  def _wrapper(f):
    arg_pos = _arg_pos(f, var)

    @evil_wraps(f)
    def _wrapped(*args, **kw):
      cache_ref = kw.get('cache_ref', None)
      if not cache_ref:
        return f(*args, **kw)

      cache_func = getattr(cache_ref, target, None)
      if not cache_func:
        return f(*args, **kw)

      try:
        var_value = args[arg_pos]
        rv = cache_func(var_value)
        if rv:
          args[arg_pos] = rv
      except IndexError:
        var_value = kw.get(var)
        rv = cache_func(var_value)
        if rv:
          kw[var] = rv

      return f(*args, **kw)
    return _wrapped
  return _wrapper


def readthrough(target, var):
  """Read-through cache for simple lookups."""
  def _wrapper(f):
    arg_pos = _arg_pos(f, var)

    @evil_wraps(f)
    def _wrapped(*args, **kw):
      cache_ref = kw.get('cache_ref', None)
      if not cache_ref:
        return f(*args, **kw)

      cache_func = getattr(cache_ref, target, None)
      if not cache_func:
        return f(*args, **kw)

      try:
        var_value = args[arg_pos]
      except IndexError:
        var_value = kw.get(var)

      rv = cache_func(var_value)
      if rv:
        return rv

      rv = f(*args, **kw)
      if rv:
        cache_func(var_value, rv)

      return rv
    return _wrapped
  return _wrapper


class CachedString(object):
  """Descriptor shortcut for caching stuff."""
  template = '%s-%s'

  def __init__(self, var, parent=None):
    self.var = var
    self.parent = parent

  def __get__(self, obj, objtype):
    return self.__class__(self.var, parent=obj)

  def __call__(self, key, value=UNSET):
    assert self.parent, 'Must be accessed as descriptor.'
    if value is UNSET:
      return self.parent.get(self.template % (self.var, key), None)
    self.parent.set(self.template % (self.var, key), value)


class CachedStringWithLookup(CachedString):
  """Cached string that knows how to look up a variety of values."""

  def __call__(self, key, value=UNSET, lookup=True):
    """If the cache call fails, attempt to lookup and then add to cache."""
    rv = super(CachedStringWithLookup, self).__call__(key, value)
    if lookup and value is UNSET and not rv:
      f = getattr(self.parent, '_lookup_%s' % self.var, None)
      if not f:
        return None
      rv = f(key)
      if rv is not None:
        self.parent.set(self.template % (self.var, key), rv)
    return rv


class Cache(object):
  image_id = CachedStringWithLookup('image_id')
  tenant_id = CachedStringWithLookup('tenant_id')
  tenant_name = CachedStringWithLookup('tenant_name')
  flavor_id = CachedStringWithLookup('flavor_id')

  def __init__(self, *args, **kw):
    self._data = dict(*args, **kw)

  def get(self, *args, **kw):
    return self._data.get(*args, **kw)

  def set(self, key, value):
    self[key] = value

  def __setitem__(self, *args, **kw):
    self._data.__setitem__(*args, **kw)

  def __getitem__(self, *args, **kw):
    return self._data.__getitem__(*args, **kw)

  def to_dict(self):
    return self._data


class JsonCache(Cache):
  """Naive cache that saves to a file on disk."""

  def __init__(self, path):
    self.path = path
    data = {}
    try:
      data = json.load(open(self.path))
    except (IOError, OSError, ValueError):
      pass
    super(JsonCache, self).__init__(data)

  def _save(self):
    try:
      json.dump(self.to_dict(), open(self.path, 'w'))
    except (IOError, OSError):
      pass

  def __setitem__(self, *args, **kw):
    super(JsonCache, self).__setitem__(*args, **kw)
    self._save()


class JsonCacheWithLookup(JsonCache):
  """Cache that will attempt to lookup values it doesn't have cached.

  This is probably only particularly useful on the command-line, as in
  a production situation you probably want to be aware of when you do
  the lookups and optimize.

  This also requires making what is probably a circular reference by keeping
  track of the api_ref.
  """

  def __init__(self, path, api_ref):
    super(JsonCacheWithLookup, self).__init__(path)
    self.api_ref = api_ref

  def _lookup_image_id(self, image_name):
    # Set cache_ref to none to prevent recursive lookups
    try:
      image_id = self.api_ref.glance.image_id(image_name, cache_ref=None)
    except requests.exceptions.HTTPError:
      return None
    except Exception:
      return image_name
    return image_id

  def _lookup_tenant_name(self, tenant_id):
    # Set cache_ref to none to prevent recursive lookups
    try:
      tenant_name = self.api_ref.keystone.tenant_name(
          tenant_id, cache_ref=None)
    except requests.exceptions.HTTPError:
      return None
    return tenant_name

  def _lookup_tenant_id(self, tenant_name):
    # Set cache_ref to none to prevent recursive lookups
    try:
      tenant_id = self.api_ref.keystone.tenant_id(tenant_name, cache_ref=None)
    except requests.exceptions.HTTPError:
      return None
    return tenant_id

  def _lookup_flavor_id(self, flavor_name):
    # Set cache_ref to none to prevent recursive lookups
    try:
      flavor_id = self.api_ref.nova.flavor_id(flavor_name, cache_ref=None)
    except requests.exceptions.HTTPError:
      return None
    return flavor_id




