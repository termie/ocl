import argparse
import getpass
import inspect
import json
import logging
import os
import pprint

import yaml

from ocl import api
from ocl import auth
from ocl import cache
from ocl.service import keystone


TOKEN_CACHE_NAME = '.token_cache'


class AlwaysHelpArgumentParser(argparse.ArgumentParser):
  def format_usage(self):
    return self.format_help()


class AppendApiAction(argparse.Action):
  """Action that lets you add arbitrary APIs from YAML files."""

  def __init__(self, *args, **kw):
    super(AppendApiAction, self).__init__(*args, **kw)

  def __call__(self, parser, namespace, values, option_string=None):
    path = values[0]
    print 'Appending auto-generated API from file: %s' % path
    name = os.path.splitext(os.path.basename(values[0]))[0]
    methods = yaml.load(open(path).read())
    service = api.api_factory(name, methods, api.MODELS)
    _add_subparser_for_service(parser.subparsers, name, service)


auth_args = argparse.ArgumentParser(add_help=False)
auth_group = auth_args.add_argument_group('authentication')
auth_group.add_argument('-u', '--user', dest='auth_user',
                       help='defaults to $OS_USERNAME')
auth_group.add_argument('-t', '--tenant', dest='auth_tenant',
                       help='defaults to $OS_TENANT_NAME')
auth_group.add_argument('-p', '--password', dest='auth_password',
                       help='defaults to $OS_PASSWORD')
auth_group.add_argument('-k', '--auth_url', dest='auth_url',
                       help='defaults to $OS_AUTH_URL')


global_args = argparse.ArgumentParser(add_help=False)
global_group = global_args.add_argument_group('global')
global_group.add_argument('--debug',
                       dest='global_debug',
                       action='store_true',
                       help='print debug info')
global_group.add_argument('--cachefile',
                       dest='global_cachefile',
                       metavar='FILE',
                       default='.ocl_cache',
                       help='specify a cachefile to use')
global_group.add_argument('--nocache',
                       dest='auth_nocache',
                       action='store_true',
                       help='do not use any caching')
global_group.add_argument('--clean',
                       dest='auth_clean',
                       action='store_true',
                       help='destroy all cache files')
global_group.add_argument('--yolo',
                          dest='global_yolo',
                          nargs=1,
                          action=AppendApiAction,
                          help='given a YAML file, add an api')



class Parser(object):
  def __init__(self, api_ref):
    self.api = api_ref
    self.parser = AlwaysHelpArgumentParser('ocl',
                                           parents=[auth_args, global_args])
    self.subparsers = self.parser.add_subparsers()
    self.subparsers.metavar = 'SUBCOMMAND'
    self.parser.subparsers = self.subparsers
    self.service_parsers = {}
    #self._add_auth_args()
    #self._add_global_args()
    self._add_noop_args()

  def _add_noop_args(self):
    p = self.subparsers.add_parser('noop', help='Do nothing. And like it.')
    p.set_defaults(func=lambda *a, **k: 'You look very nice today.')


  def parse_args(self):
    return self.parser.parse_args()


def _add_subparser_for_service(subparsers, name, service):
  """Generate the CLI parser for an instance.

  This is significantly more complicated looking than normal because
  we use descriptors for the auto-generated API and decorators liberally.
  """

  # Description for the service
  service_doc = 'UNDOCUMENTED'
  if service.__doc__:
    service_doc = service.__doc__.split('\n')[0]

  # First level subparser: the service
  sp = subparsers.add_parser(name,
                             help=service_doc)

  # Second level subparser: the method
  second = sp.add_subparsers()
  second.metavar = 'METHOD'

  for method_name in dir(service):
    # Skip internal methods and non-callables
    if method_name.startswith('_'):
      continue
    method = getattr(service, method_name)
    if not callable(method):
      continue

    # Get the docstring
    method_desc = method.__doc__ and method.__doc__ or 'UNDOCUMENTED'
    method_help = method_desc.split('\n')[0]


    # Deal with our descriptors
    if isinstance(method, api.ApiMethod):
      method = getattr(method, '__call__')

    # Each method is its own parser
    p = second.add_parser(method_name,
                          help=method_help,
                          description=method_desc)

    # Set an attribute to remember the callable for the method
    p.set_defaults(func=method)

    # Take a long hard look at our method / your life
    args, varargs, keywords, defaults = inspect.getargspec(method)

    # Special case for now, deal with free-form stuff for testing
    if varargs:
      p.add_argument('args', nargs=argparse.REMAINDER)
      continue

    # Match up the positional args to their names
    # These are reversed and re-reversed because defaults are given
    # in the reverse order.
    args = list(reversed(args))
    l = []
    for i, arg in enumerate(args):
      # Skip our special args
      if arg in ('self', 'auth_ref', 'cache_ref'):
        continue

      # Build up the argparse argument
      arg_name = arg
      params = {'help': _get_param_help(arg_name, method)}
      try:
        params['default'] = defaults[i]
        params['required'] = False
        arg_name = '--' + arg
      except (IndexError, TypeError):
        pass
      l.append((arg_name, params))

    for arg_name, params in reversed(l):
      p.add_argument(arg_name, **params)


def _get_param_help(arg_name, method):
  """Get the help for a parameter.

  Right now this is not implemented but it should probably look up the
  variable names from somewhere.
  """
  return 'UNDOCUMENTED'


class DirectParser(Parser):
  def __init__(self, *args, **kw):
    super(DirectParser, self).__init__(*args, **kw)
    self._build_from_api(self.api)

  def _build_from_api(self, api_ref):
    """Build a command tree from an Api instance."""

    services = dict((k, getattr(api_ref, k)) for k in dir(api_ref)
                  if not k.startswith('_'))
    for name, handle in services.iteritems():
      self._build_from_service(name, handle)

  def _build_from_service(self, name, handle):
    _add_subparser_for_service(self.subparsers, name, handle)


class CommandLine(object):
  def _load_cached_token(self):
    try:
      return json.load(open(TOKEN_CACHE_NAME))
    except Exception:
      return None

  def _clear_cached_token(self):
    try:
      os.unlink(TOKEN_CACHE_NAME)
    except OSError as e:
      if e.errno != 2:
        raise

  def _set_cached_token(self, token):
    json.dump(token, open(TOKEN_CACHE_NAME, 'w'), indent=2)

  def _get_auth_user(self, parsed):
    if parsed.auth_user:
      return parsed.auth_user
    if 'OS_USERNAME' in os.environ:
      return os.environ['OS_USERNAME']
    user = raw_input('Username: ').strip()
    parsed.auth_user = user
    return user

  def _get_auth_password(self, parsed):
    if parsed.auth_password:
      return parsed.auth_password
    if 'OS_PASSWORD' in os.environ:
      return os.environ['OS_PASSWORD']
    password = getpass.getpass()
    parsed.auth_password = password
    return password

  def _get_auth_tenant(self, parsed):
    if parsed.auth_tenant:
      return parsed.auth_tenant
    if 'OS_TENANT_NAME' in os.environ:
      return os.environ['OS_TENANT_NAME']
    tenant = raw_input('Tenant: ').strip()
    parsed.auth_tenant = tenant
    return tenant

  def _get_auth_url(self, parsed):
    if parsed.auth_url:
      return parsed.auth_url
    if 'OS_AUTH_URL' in os.environ:
        return os.environ['OS_AUTH_URL']
    url = raw_input('Auth URL: ').strip()
    parsed.auth_url = url
    return parsed.auth_url

  def _authenticate_interactive(self, parsed):
    user = self._get_auth_user(parsed)
    password = self._get_auth_password(parsed)
    tenant = self._get_auth_tenant(parsed)
    auth_url = self._get_auth_url(parsed)

    ks_client = keystone.Keystone()

    token = ks_client.authenticate(user=user,
                                   password=password,
                                   tenant=tenant,
                                   auth_url=auth_url)

    return token

  def main(self):
    api_ref = api.Api()
    parser = DirectParser(api_ref)
    parsed = parser.parse_args()

    if parsed.global_debug:
      logging.getLogger().setLevel(logging.DEBUG)

    # Authenticate
    if parsed.auth_clean:
      self._clear_cached_token()

    token = None
    if not parsed.auth_nocache:
      token = self._load_cached_token()

    if not token:
      token = self._authenticate_interactive(parsed)
      if not parsed.auth_nocache:
        self._set_cached_token(token)

    auth_ref = auth.Auth.from_authenticate(token)

    # NOTE(termie): allow overriding the keystone admin url because many
    #               don't return a valid admin url in the catalog
    if parsed.auth_url:
      auth_ref.catalog['identity'].admin_url = parsed.auth_url

    # Setup cache
    if not parsed.auth_nocache:
      cache_ref = cache.Cache()
      if parsed.global_cachefile:
        authed_api = api.Authenticated(api_ref, auth_ref)
        cache_ref = cache.JsonCacheWithLookup(parsed.global_cachefile,
                                              authed_api)
    else:
      cache_ref = None

    # Call the command
    args = dict((k, v) for k, v in vars(parsed).iteritems()
                if k != 'func'
                   and not k.startswith('auth')
                   and not k.startswith('global'))
    args['auth_ref'] = auth_ref
    args['cache_ref'] = cache_ref
    #print args
    if 'args' in args:
      positionals = args['args']
      del args['args']
      pprint.pprint(parsed.func(*positionals, **args), indent=2)
    else:
      pprint.pprint(parsed.func(**args), indent=2)


def main():
  c = CommandLine()
  c.main()
