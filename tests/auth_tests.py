from ocl import test


class AuthTests(test.ApiTestCase):
  # TODO(termie): this should check for a more specific exception when
  #               we have some, right now it is catching a KeyError
  def test_auth_failed(self):
    with test.Flow('auth_failed') as flow:
      self.assertRaises(Exception, self.authenticate)
