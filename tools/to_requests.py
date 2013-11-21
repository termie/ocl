import json

def request_to_dict(req):
  o = {}
  d = dict((k.lower(), v) for k, v in req.headers.lst)
  o['headers'] = d
  o['content'] = req.content
  o['path'] = req.path
  o['method'] = req.method
  o['port'] = req.port
  o['host'] = req.host
  o['scheme'] = req.scheme
  o['url'] = req.get_url()

  q = dict((k, v) for k, v in req.get_query().lst)
  o['query'] = q

  return o


def response_to_dict(res):
  o = {}
  d = dict((k.lower(), v) for k, v in res.headers.lst)
  o['headers'] = d
  o['code'] = res.code
  o['msg'] = res.msg
  o['content'] = res.content
  return o


# Global so we can dump everything at the end
final_output = []

def response(context, flow):
  try:
    req = request_to_dict(flow.response.request)
    res = response_to_dict(flow.response)
    final_output.append({'request': req,
                         'response': res})
  except Exception as e:
    print e

def done(context):
  print json.dumps(final_output, indent=2)
