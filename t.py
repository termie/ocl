
import pprint

from ocl import api
from ocl import auth
from ocl.service import keystone


USER='termie'
PASSWORD='termie'
TENANT='termie'
KEYSTONE_HOST='keystone.yourcloud.com'


def p(o):
  pprint.pprint(o, indent=2)

def main():

  ks_client = keystone.Keystone(KEYSTONE_HOST)

  token = ks_client.authenticate(user=USER,
                                 password=PASSWORD,
                                 tenant=TENANT)

  auth_ref = auth.Auth.from_authenticate(token)

  p(token)
  p(auth_ref.catalog['image'].public_url)
  a = api.Authenticated(api.CoreApi(), auth_ref)
  rv = a.glance.list_images()
  p(rv)

if __name__ == '__main__':
  main()
