HOLY FUCKING SHIT IT IS OCL
===========================

This is a command-line tool and a library. To control all of Openstack

It has an external dependency on 'requests' so you'll need that.
And 'warlock.'

Still very thrown together, but here's sort of what's going on.


--------------------
Get The Fuck Started
--------------------

Things are progressing quickly. At the moment your best bet is to do something
like::

  $ git checkout termie/ocl
  $ pip install -e .
  $ ocl --help


--------------------
Helping The Fuck Out
--------------------

Try running the commands, when they fail, `post an issue`_.

 .. _`post an issue`: https://github.com/termie/ocl/issues


--------------------
Command-line Example
--------------------

When you first run it, ocl will ask for some credentials, it will cache the
token it gets back from authentication so that you won't have to do it often.

If you don't want to cache the token use the ``--nocache`` flag.

If you want to delete the token cache use the ``--clean`` flag.

If you don't want to type the auth url you can set an env var ``OCL_AUTH_URL``

::

  # For now it is just easier to export the Auth URL as an environment
  # variable. Technically you can type it in once to get the token, but
  # if the admin_url for keystone in the catalog is wrong you'll run into
  # weird problems later on...

  $> export OS_AUTH_URL=http://keystone.yourcloud.com:35357/v2.0

  $> ocl glance list_images

  Username: termie
  Password:
  Tenant: termie
  Auth URL:
  { u'images': [ { u'checksum': u'61ef5ae8984a99e4edcb2e9424e2c544',
                 u'container_format': u'ovf',
                 u'disk_format': u'qcow2',
                 u'id': u'0aceee71-d642-4226-8598-d93c1d8e9947',
                 u'name': u'centos 6.3 amd64 with OGE',
                 u'size': 1035337728},
               { u'checksum': u'a9afa0a5c816c6b0ce3367f7adc53ba2',
                 u'container_format': u'ovf',
                 u'disk_format': u'qcow2',
                 u'id': u'32415a96-4ad8-432e-b32a-a5997f91e249',
                 u'name': u'biotech-explorer-0.1',
                 u'size': 2020737024},
                 ...


  $> ocl glance list_images --help

  usage: ocl glance list_images [-h] [--name NAME]

  optional arguments:
    -h, --help   show this help message and exit
    --name NAME

  $> ocl glance list_images --name foo

  { u'images': [ { u'checksum': u'dfed728d43c5d7020d9388d9149cc468',
                   u'container_format': u'ovf',
                   u'disk_format': u'qcow2',
                   u'id': u'7e43a17c-17fa-4083-b2ec-b838ac74b87b',
                   u'name': u'foo',
                   u'size': 1689452544}]}


Here's an example of what might happen if you show the default help right now::

  (ocl)termie@cody:~/p/ocl % ocl --help
  usage: ocl [-h] [-u AUTH_USER] [-t AUTH_TENANT] [-p AUTH_PASSWORD]
             [-k AUTH_URL] [--nocache] [--clean] [--debug]
             [--cachefile GLOBAL_CACHEFILE]
             {noop,catalog,keystone,glance,nova} ...

  positional arguments:
    {noop,catalog,keystone,glance,nova}
                          Sub-commands
      noop                Do nothing. And like it.
      catalog
      keystone
      glance
      nova

  optional arguments:
    -h, --help            show this help message and exit
    -u AUTH_USER, --user AUTH_USER
    -t AUTH_TENANT, --tenant AUTH_TENANT
    -p AUTH_PASSWORD, --password AUTH_PASSWORD
    -k AUTH_URL, --auth_url AUTH_URL
    --nocache
    --clean
    --debug
    --cachefile GLOBAL_CACHEFILE


Try it out!

---------------
Library Example
---------------

::

  from ocl import api
  from ocl import auth


  auth_ref = auth.authenticate(
      auth_url=KEYSTONE_URL, user=USER, password=PASSWORD, tenant=TENANT)
  apee = api.Authenticated(api.Api(), auth_ref)

  rv = apee.glance.list_images(name='foo')
  print rv['images'][0]['id']



Great Minds Are Skeptical
=========================

-----------------------------------------
First You Authenticate, Then You Do Stuff
-----------------------------------------

This has a couple nice features:

  1. You always know whether you have authenticated already before again.
  2. You can cache the authentication token.
  3. The authentication scheme is decoupled.


Y'already Know, Buddy
---------------------

Isn't it annoying wondering whether your API call is going to make another
call to authenticate before it actually makes your call, but only sometimes
so you don't really have any idea how long it is going to take THIS time
you make the call. Yeah.

Hey, so if you do your authentication beforehand, you know you did your
authentication already. Isn't that cool? Yeah it is. Get used to that cool
feeling, you're about to have a bunch of it::

  from ocl import auth

  auth_ref = auth.authenticate(auth_url=AUTH_URL,
                               user=USER,
                               password=PASSWORD,
                               tenant=TENANT)

  # You're gonna love this auth_ref. Boom.


Cache Rules Everything Around Me
--------------------------------

Hey there. Stop. Listen. Why are you authenticating all the damn time?
Do you like typing your password into things? Do you like saving it in files?
I sure as hell don't and I'm willing to bet you don't either.

Screw that stuff.

By default, the command-line client will cache your auth token. Speeds stuff
right up. But since you are a cool programmer you'll probably want to do your
own cool caching and because auth is separate YOU CAN. Easily::

  auth_dict = auth_ref.to_dict()

  auth_ref = auth.Auth(**auth_dict)

  # This doesn't work yet. TODO(termie): remove this when it does work.


We'll Always Love You As Long As You're Perfect
-----------------------------------------------

Because auth basically just has to provide some data that the API knows how to
take advantage of, it can do anything it needs to in order to get that data.
Anything. As long as it's good data we'll look the other way::

  import crazy_auth

  crazy_auth_ref = crazy_auth.lie_about_everything()

  # Haha. Oh man, that auth is so crazy. -wipes tears from eyes-


-------------------
We Can Be Explorers
-------------------

Actually, Openstack pretty much forces you to be, so let's solve this
whole discovery debacle. Let's be really, really aggressive about figuring
out where all the calls we want to make should be going and what they should
look like.

Hell, let's make it a whole module dedicated to weeding out and generating a
cacheable object that will tell us where we want to send our calls, and maybe
even which calls we can send, and MAYBBBBBEEEEE even what those calls should
look like.


The "Service Catalog"
---------------------

What do we know already? Well, we have an AUTH_URL, and assuming we've got
some valid credentials, that should net us a "Service Catalog" with our
token request.

That "Service Catalog" is sort of like a list of suggestions as to where we
should target our requests, some of the services actually want us to make
another request to find out where specifically to send the requests for that
specific service.

They also give us a variety of urls, some of which aren't even valid, because
hey, why not.


ocl discovery discover
----------------------

We included a discovery mechanism to help you build a list of available
endpoints, you can run it from the command-line to get the raw output.

Right now it starts with the service catalog returned in your auth token,
and does some heuristics based on urls and data returned from urls to
build up the list of available services, regions, endpoints, versions, etc::

  (ocl)termie@champs:~/p/ocl % ocl discovery discover

  { 'endpoints': [ { 'access': 'public',
                     'endpoint': u'http://example:8774/v2/someuuid',
                     'name': u'nova',
                     'region': u'RegionOne',
                     'service': u'compute',
                     'version': u'v2'},
                   { 'access': 'public',
                     'endpoint': u'http://example:9696/v2.0',
                     'name': u'network',
                     'region': u'RegionOne',
                     'service': u'network',
                     'version': u'v2.0'},
                   { 'access': 'public',
                     'endpoint': u'http://example:9292/v2/',
                     'name': u'glance',
                     'region': u'RegionOne',
                     'service': u'image',
                     'version': u'v2.1'},
                   { 'access': 'public',
                     'endpoint': u'http://example:9292/v2/',
                     'name': u'glance',
                     'region': u'RegionOne',
                     'service': u'image',
                     'version': u'v2.0'},
                   { 'access': 'public',
                     'endpoint': u'http://example:9292/v1/',
                     'name': u'glance',
                     'region': u'RegionOne',
                     'service': u'image',
                     'version': u'v1.1'},
                   { 'access': 'public',
                     'endpoint': u'http://example:9292/v1/',
                     'name': u'glance',
                     'region': u'RegionOne',
                     'service': u'image',
                     'version': u'v1.0'},
                   { 'access': 'public',
                     'endpoint': u'http://example:8776/v1/someuuid',
                     'name': u'cinder',
                     'region': u'RegionOne',
                     'service': u'volume',
                     'version': u'v1'},
                   { 'access': 'public',
                     'endpoint': u'http://example:8888/swift/v1',
                     'name': u'swift',
                     'region': u'RegionOne',
                     'service': u'object-store',
                     'version': u'v1'},
                   { 'access': 'admin',
                     'endpoint': u'http://example:35357/v2.0',
                     'name': u'keystone',
                     'region': u'RegionOne',
                     'service': u'identity',
                     'version': u'v2.0'},
                   { 'access': 'public',
                     'endpoint': u'http://example:5000/v2.0',
                     'name': u'keystone',
                     'region': u'RegionOne',
                     'service': u'identity',
                     'version': u'v2.0'}]}

In some ways this is more verbose and in other ways less verbose, than the
default "service catalog" returned with your token, but it is definitely
more useful. Especially when used as a library!


ocl.discovery.Endpoints
-----------------------

When used as a library, the discovery call hands you back a very pleasant
to use Endpoints data object. Examples::

  from ocl import api
  auth_ref = auth.authenticate(...)
  apee = api.Api()

  endpoints = apee.discovery.discover(auth_ref=auth_ref)

  # List services available
  rv = endpoints.services()
  # [u'compute', u'identity', u'image', u'network', u'object-store', u'volume']

  # Or the versions of the image service available
  rv = endpoints.versions('image')
  # [u'v1.0', u'v1.1', u'v2.0', u'v2.1']

  # Or ask for a specific version
  rv = endpoints.endpoint('image', version='v2.1')
  # { 'access': 'public',
  #   'endpoint': u'http://example:9292/v2/',
  #   'name': u'glance',
  #   'region': u'RegionOne',
  #   'service': u'image',
  #   'version': u'v2.1'}

Have fun, champs.

--------------
State No State
--------------


I Don't Know What A Monad Is
----------------------------

But that doesn't mean we can't try to make our interfaces conform to some
vaguely functional ideas.

The vast majority of API methods (all methods that result in an authenticated
call) require an ``auth_ref`` parameter that is always passed as a keyword.::

  from ocl import api
  from ocl import auth

  auth_ref = auth.authenticate(...)
  apee = api.Api()

  images = apee.glance.list_image(auth_ref=auth_ref)

  # Remember that it auth_ref always passed as a keyword


Let's Pretend We Know Stuff Though
----------------------------------

Typing all that stuff can be soooooooooo tiring. I got so tired writing this
that I didn't even fill in the argument names for all the filters you can use
in a lot of places. Hah!

Nobody wants to type that silly stuff in all the time, so there's a helper
that sort of like provides you with a version of the API that doesn't need
all that because it wraps the methods and passes the ``auth_ref`` in
automatically::

  from ocl import api
  from ocl import auth

  auth_ref = auth.authenticate(...)
  apee = api.Authenticated(api.Api(), auth_ref)

  images = apee.glance.list_image()

  # You can probably forget most of that stuff about keywords


Caching Too!
------------

The same model works with caching, too. Every method takes a ``cache_ref``
parameter, but we also have a wrapper for that::

  from ocl import api
  from ocl import auth
  from ocl import cache

  auth_ref = auth.authenticate(...)
  cache_ref = cache.Cache()
  apee = api.Cached(api.Authenticated(api.Api(), auth_ref), cache_ref)

  # This will cache all the image id / name mappings, for example
  images = apee.glance.list_images()

  # This won't have to make an http call! Cool!
  some_id = apee.glance.image_id(some_name)


-----------
Data Stuffs
-----------

Openstack has a weird API, don't even try to pretend it doesn't.

I hate having to think about what crazy organization different responses
have, but I also hate having to use (other) people's crazy object models.

As expected, we're going to let you do either.


Raw Deal
--------

The basics when you use any of the API methods will in almost all cases give
you back a basic dictionary that is a direct copy of the parsed result::

  from ocl import api

  a = api.PluginApi()
  rv = a.some_method()
  rv['some_value']


Actually, That Was A Lie
------------------------

Turns out that wasn't a basic dictionary. We'd apologize for lying to you,
but we don't know you and I don't care about your feelings.

Just kidding, we love you.

That thing we returned is actually smart and stuff, so even though it _looks_
like a dictionary to your pathetic little eyes, it actually has a power level
over 9000::

  from ocl import api

  a = api.PluginApi()
  rv = a.glance.list_images()

  # The response of the list images call looks a lot like
  {'images': [
    {'some_image_property': 'foo',},
    {'some_image_property': 'bar',},
    ]
   }

  rv['images']  # would look like the list from the above dict

  # But rv is actually an ImageCollection instance so you can treat it
  # like an iterator of Image instances.
  for image in rv.images:
    print image.size


------------------
Command-Line Sugar
------------------

Because half of the goal of this bad boy is to provide you, Sir User, a
wicked great command-line interface, we did some nice things for you.

  1. Auth token caching.
  2. Automatic name / id lookup and conversion.
  3. Lazy extensibility.


Stop Authenticating, Start Being Already Authenticated
------------------------------------------------------

The command-line tool defaults to caching your authentication token (not
username or password) so that you don't have to authenticate so often.

If you want to clear that cache, just run your command with ``--clean`` or you
can avoid caching with ``--nocache``.


Stop Typing UUIDs, Start ... Not Typing UUIDs
---------------------------------------------

The command-line tool defaults to using a caching and lookup mechanism to
automagically convert things like flavor names to flavor IDs.

Whenever possible, if a call requires a tenant ID or flavor ID or image ID,
we will lookup the appropriate mapping and insert it into the call. We'll
also cache it locally so you don't have to make that lookup again.


Stop ... Whatever
-----------------

Besides the extensibility through the plugin model, you can also write
arbitrary tools to tie in to OCL just by adding an executable to your path
that starts with ``ocl-``, for example if you had ``ocl-party`` then calling
``ocl party foo`` with call ``ocl-party`` with the argument ``foo``.

Just a nicety, but sometimes people want that.

# TODO(termie): This doesn't work either.


------------------
Extend And Conquer
------------------

Openstack has way too many extensions and so can you.

  1. New Services.
  2. New Calls.
  3. ALTERED REALITY.


General Mechanism
-----------------

We use ``setuptools`` for the basic unit of extensibility for the API and CLI.

We add the registration functions for everything we want in our API to the
``ocl.api.plugins`` entry point. For example, in our ``setup.py``::

  config = dict(
      name='ocl',
      ...
      entry_points={
          ...
          'ocl.api.plugins': [
              'glance = ocl.service.glance:register',
              'nova = ocl.service.nova:register',
              'keystone = ocl.service.keystone:register',
          ]
      },
  )


A Whole New World
-----------------

The easiest and cleanest way to extend OCL is by adding support for an
additional service::

  from ocl import plugin


  class NewService(plugin.Service):
    catalog_type = 'new_service'

    def some_call(self, auth_ref=None, cache_ref=None):
      pass


  # Register this class with the api and auto-generate the CLI.
  # It will be available as the `newservice` attribute on the PluginApi.
  def register():
    plugin.lazy_api('newservice', NewService())


A Whole New... Country
----------------------

Providing a new call for an existing service isn't a whole lot different::

  from ocl import plugin
  from ocl.service import some_service

  class ExtendedService(some_service.Existing):
    def new_call(self, auth_ref=None, cache_ref=None):
      pass


  # Register the call with the api and auto-generate the CLI.
  # It will be available as the `new_call` method on the `some_service`
  # attribute on the PluginApi.
  def register():
    plugin.lazy_api('some_service.new_call', ExtendedService().new_call)


Let's Just Change Anything
--------------------------

Welcome to hell. Just kidding, mostly, this is basically a way to overload
an existing call. The API is very low-level because it lets to do something
kind of awkward, it lets you modify the request slightly before it gets
called::

  from ocl import plugin
  from ocl.service import some_service

  class OverloadedService(some_service.Existing):
    def list_images(self, orig_arg, extra_arg, auth_ref=None, cache_ref=None):

      # This will be called with the original _get as the first argument
      def get_wrapper(f, url, params, headers=None, **kw):
        params['extra_arg'] = extra_arg
        return f(url, params, headers=headers, **kw)

      # Replace the original _get on the class with this cool new get for the
      # duration of the original call.
      # TODO(termie): this doesn't work yet either
      with plugin.overload(self, '_get', get_wrapper):
        super(OverloadedService, self).list_images(
            orig_arg, auth_ref=auth_ref, cache_ref=cache_ref)

  # Replace the original call. This kills the crab.
  def register():
    plugin.lazy_api('some_service.list_images', OverloadedService().list_images)
