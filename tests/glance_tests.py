import json
import cStringIO as StringIO

from ocl import auth
from ocl.http import client as http
from ocl import test
from ocl.service import glance

import mock


class GlanceTests(test.ApiTestCase):

  def test_auth_and_list_images(self):
    flow = test.load_flow('auth_and_list_images')
    glance_auto = glance.GlanceAuto()

    with test.Flow('auth_and_list_images') as flow:
      auth_ref = self.authenticate()
      #print auth_ref.catalog
      images = glance_auto.list_images(auth_ref=auth_ref)
      #print images
