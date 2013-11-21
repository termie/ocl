from ocl import api


def lazy_api(target, inst):
  api.Api._REGISTRY[target] = inst
