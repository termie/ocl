import functools

import warlock

model_factory = warlock.model_factory

def request_factory(schema):
  model = model_factory(schema)

  @functools.wraps(model)
  def _request_builder(kw):
    filtered_kw = dict((k, v) for k, v in kw.iteritems()
                       if k in schema['properties'])
    d = {schema['name']: filtered_kw}
    return model(d)

  return _request_builder
