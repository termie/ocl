import json
import logging
import pprint
import re

from ocl import api
from ocl import plugin


logger = logging.getLogger(__name__)


"""Example raw catalog response:

[ { u'endpoints': [ { u'adminURL': u'http://example:8774/v2/someuuid',
                      u'internalURL': u'http://example:8774/v2/someuuid',
                      u'publicURL': u'http://example:8774/v2/someuuid',
                      u'region': u'RegionOne'}],
    u'endpoints_links': [],
    u'name': u'nova',
    u'type': u'compute'},
  { u'endpoints': [ { u'adminURL': u'http://example:9696/',
                      u'internalURL': u'http://example:9696/',
                      u'publicURL': u'http://example:9696/',
                      u'region': u'RegionOne'}],
    u'endpoints_links': [],
    u'name': u'network',
    u'type': u'network'},
  { u'endpoints': [ { u'adminURL': u'http://example:9292',
                      u'internalURL': u'http://example:9292',
                      u'publicURL': u'http://example:9292',
                      u'region': u'RegionOne'}],
    u'endpoints_links': [],
    u'name': u'glance',
    u'type': u'image'},
  { u'endpoints': [ { u'adminURL': u'http://example:8776/v1/someuuid',
                      u'internalURL': u'http://example:8776/v1/someuuid',
                      u'publicURL': u'http://example:8776/v1/someuuid',
                      u'region': u'RegionOne'}],
    u'endpoints_links': [],
    u'name': u'cinder',
    u'type': u'volume'},
  { u'endpoints': [ { u'adminURL': u'http://example:8773/services/Admin',
                      u'internalURL': u'http://example:8773/services/Cloud',
                      u'publicURL': u'http://example:8773/services/Cloud',
                      u'region': u'RegionOne'}],
    u'endpoints_links': [],
    u'name': u'ec2',
    u'type': u'ec2'},
  { u'endpoints': [ { u'adminURL': u'http://example:8888/swift/v1',
                      u'internalURL': u'http://example:8888/swift/v1',
                      u'publicURL': u'http://example:8888/swift/v1',
                      u'region': u'RegionOne'}],
    u'endpoints_links': [],
    u'name': u'swift',
    u'type': u'object-store'},
  { u'endpoints': [ { u'adminURL': u'http://example:35357/v2.0',
                      u'internalURL': u'http://example:5000/v2.0',
                      u'publicURL': u'http://example:5000/v2.0',
                      u'region': u'RegionOne'}],
    u'endpoints_links': [],
    u'name': u'keystone',
    u'type': u'identity'}]
"""


RE_VERSION = re.compile(r"""/(v\d\.?\d*)/?""")


def version_in_url(url):
  m = RE_VERSION.search(url)
  if m:
    return m.group(1)
  return None


class Discovery(object):
  def discover(self, raw_catalog=None, auth_ref=None, cache_ref=None):
    """Try hard to figure out what we're doing."""
    if not raw_catalog:
      raw_catalog = auth_ref.raw_catalog

    logger.debug(pprint.pformat(raw_catalog))

    o = []

    for service in raw_catalog:
      if service['type'] == 'ec2':
        # TODO(termie): maybe we do care about ec2?
        continue

      for region in service['endpoints']:
        public = region.get('publicURL')
        admin = region.get('adminURL')
        internal = region.get('internalURL')

        to_check = {'public': public}
        if admin != public:
          to_check['admin'] = admin
        if internal != public:
          to_check['internal'] = internal

        for access, url in to_check.iteritems():
          logger.info('Checking service "%s"', service['type'])
          logger.info('    %s endpoint "%s"', access, region['region'])
          logger.info('    at "%s"', url)

          explicit_version = version_in_url(url)
          if explicit_version:
            logger.info('  found version in url: %s', repr(explicit_version))
            logger.info('    at: %s', url)

            o.append({'service': service['type'],
                      'name': service['name'],
                      'access': access,
                      'region': region['region'],
                      'endpoint': url,
                      'version': explicit_version})
            continue

          tester = api.get(url=url,
                           auth_ref=auth_ref)
          logger.debug('RESPONSE:\n%s', tester.content)

          try:
            rv = json.loads(tester.content)
            #logger.debug(pprint.pformat(rv))
          except Exception as e:
            logger.debug('FAILED TO PARSE JSON')
            continue

          if 'versions' in rv:
            for version in rv['versions']:
              v_id = version.get('id')
              v_url = version['links'][0]['href']
              logger.info('  found version: %s', v_id)
              logger.info('    at: %s', v_url)
              o.append({'service': service['type'],
                        'name': service['name'],
                        'access': access,
                        'region': region['region'],
                        'endpoint': v_url,
                        'version': v_id})

    eps = Endpoints({'endpoints': o})
    return eps.endpoint('image', version='v2.1')


class Endpoints(dict):
  """Data object providing a bunch of lookups for service endpoints.

  `endpoints` here is a list of endpoints in the format:

    endpoints = {'service': service_type,
                 'name': service_name,
                 'version': version_id,
                 'endpoint': url}
  """
  def __init__(self, endpoints):
    self._endpoints = endpoints['endpoints']
    super(Endpoints, self).__init__(endpoints)

  def services(self, region=None, access=None):
    """All services, possibly filtered by region."""
    services = set()
    for ep in self._endpoints:
      if region and ep['region'] != region:
        continue
      services.add(ep['service'])
    return list(sorted(services))

  def regions(self, service=None):
    """All regions, possibly filtered by service."""
    regions = set()
    for ep in self._endpoints:
      if service and ep['service'] != service:
        continue
      regions.add(ep['region'])
    return list(sorted(regions))

  def versions(self, service, region=None):
    """All versions found for a service, possibly filtered by region."""
    versions = set()
    for ep in self._endpoints:
      if ep['service'] != service:
        continue
      if region and ep['region'] != region:
        continue
      versions.add(ep['version'])
    return list(sorted(versions))

  def endpoints(self, service, version=None, region=None, access=None):
    """Return endpoints for a service, filtered by version and/or region."""
    eps = []
    for ep in self._endpoints:
      if ep['service'] != service:
        continue
      if version and ep['version'] != version:
        continue
      if region and ep['region'] != region:
        continue
      if access and ep['access'] != access:
        continue
      eps.append(ep)
    return list(sorted(eps, key=lambda x: x['version']))

  def endpoint(self, service, version=None, region=None, access=None):
    """Return 'latest' single endpoint, filtered by version, region, access."""
    eps = self.endpoints(service, version=version, region=region, access=access)
    if not eps:
      raise Exception('No endpoint found: %s' % (service, version, region))
    return eps[-1]


def register():
  plugin.lazy_api('discovery', Discovery())
