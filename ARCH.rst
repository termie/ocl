The Architecture of OCL
=======================

There's already a lot of info in the readme, this is trying to re-arrange it
into possibly a better way for somebody who wants to understand the internals.

Destruction of all things is a constant in the universe.

Here's a basic layer diagram as you drive down through the stack::

  CLI User Input Parsing
                |
  CLI Caching
                |
  CLI Function Auto-Generation from Classes and Methods
                |
  Plugin Registration
                |
  Library Class and Method Overrides and One-Offs
                |
  Library Class and Method Auto-Generation from API Definitions
                |
  API Definition Overrides and One-Offs
                |
  API Definitions from Reflection APIs
                |
  API Definition Auto-Generation from Project Codebases

That's a bunch of stuff and a lot of auto-generation but it's a brave new
world and we're willing to hold a lot of hands to bring people with us.

The water's great, let's jump in the deep end.


API Definition Auto-Generation from Project Codebases
-----------------------------------------------------

One of the big promises of OCL is to help break the endless loop of
Upgrade -> Break -> Fix -> Upgrade that occurs when managing client libraries
separately from code bases and separate from deployments.

In a world with multiple versions across multiple services across multiple
deployments version inter-compatibility is a large annoyance to interact with
and a problem to maintain. We have to be able to easily generate compatible
clients directly from the projects themselves by basing our clients off of
an intermediate API definition document.

There are two ways to do this.

--------------------------------
Project-Provided API Definitions
--------------------------------

If projects output their complete or nearly complete API definitions via their
builds or as part of their testing, we can simply pull those and include
support for that version.

There is a good incentive for a project to provide this information.

  1. It is useful information for their testing, it gives a great enumeration
     of the functionality they provide.
  2. It allows them to use OCL in their tests as it doesn't need to be
     modified to support most new functionality.
  3. It allows them to use OCL as an easy CLI to test new features during
     development.


---------------------------
Heavy Project Introspection
---------------------------

Not all projects will start off providing us this information. This is where
holding a bunch of hands comes in. We'll effectively screen-scrape the
information out of them.

  1. The easiest projects will be ones with clear API definitions in other
     formats, for those we only need to write translations.

  2. Next easiest are smaller projects that have their APIs defined in simple
     homogenous formats that can be statically analyzed to produce our
     definitions.

  3. Lastly there are projects that are large and have very dynamically defined
     interfaces, for those we'll have to load the actual code and do
     introspection.

In all these case there will be some exceptions, portions that will need to be
defined by hand. In most projects there is reasonable naming strictness such
that we can infer the data types of individual parameters based on their
names.


API Definitions from Reflection APIs
------------------------------------

The previous section on auto-generating the API definitions helps a lot with
keeping client support for many projects in sync, but more ideal would be
keeping client support for specific deployments in sync. For this we need those
deployments to provide us with the API definitions via some kind of API.

Typically these are called reflection APIs but not many of the projects in
Openstack support them yet. Projects like Glance have begun to move in this
direction with calls like:

  http://docs.openstack.org/api/openstack-image-service/2.0/content/get-images-schema.html

If the projects begin generating this data and providing it via an API there
are countless benefits for third parties. Specifically, OCL would be able
to auto-generate specific support for a specific deployment, includings its
plugins and unusual configurations.

Additionally, it would keep the projects honest. Wear your API on your sleeve.


API Definition Overrides and One-Offs
-------------------------------------

Pretty much exactly what it sounds like. From the perspective of developers
working on debugging or implementing new things, we want easy access to load
additional API definitions and have them be able to override existing
definitions.

Towards this end we allow pointing at additional API definitions from the
CLI level. From the library side the standard auto-generation (next section)
and plugin registry (a couple sectiosn down) will let you load your overrides.


Library Class and Method Auto-Generation from API Definitions
-------------------------------------------------------------

The next step up from the API definition is to build that into a useful class
that can make the actual requests to the API.

Almost all the API calls in Openstack, and in the RESTish web at large, follow
a small number of similar patterns. OCL handles most of these automatically,
even to the point of having a naive approach to filling in complex data types
based on the API definitions.

The calls themselves follow the pattern of:

  * Accept user data.
  * Optionally, use a smart cache to normalize invalid data types (e.g. names)
    to valid data types (e.g. IDs).
  * Optionally, return a cached result.
  * Optionally, attempt to munge the data into more complex data structures.
  * Validate user data.
  * Perform a simple HTTP request.
  * Check response code, on error shunt to error handling.
  * Validate response.
  * Optionally, encapsulate response in a smart data object.
  * Optionally, cache the response.
  * Return response.
  * High fives all around.

Again, this works for the vast majority of calls. But a few kinds of calls
need to send extra special data types into the ether, it is because of those
that we actually generate real classes in the code during this step, so that
you can use...


Library Class and Method Overrides and One-Offs
-----------------------------------------------

The library classes auto-generated from API definitions are real classes, and
as such you can subclass them to add special calls and do special things.

The easiest example of this would be calls that need to upload files.

Everything above the library classes in our layer diagram way at the top only
assumes callables and classes, so you can write your own classes that do
really anything you want and hook them in, via the plugin system.


Plugin Registration
-------------------

We have very simple plugin registration using setuptools entry_points. You
define a callable and pass it to the entry point::

        'ocl.api.plugins': [
            'discovery = ocl.discovery:register',
            ]

From there you can call the plugin registration functions to get your classes
into the API. Everything from this level up expects callables and classes so
go nuts.


CLI Function Auto-Generation from Classes and Methods
-----------------------------------------------------

The CLI is organized as <namespace> <verb> [params...], and this is generated
from the classes registered via the plugin system. The basic format is that
the instance object is the namespace, the method is the verb, and any further
args are passed as positional params.

Documentation is generated from docstrings and parameter names (it turns out
there aren't actually a very wide variety of parameter names in Openstack).


CLI Caching
-----------

Due to the relatively normalized set of parameter names in Openstack we can do
some caching in the CLI that allows us to automatically replace, for example,
names with IDs in many of the locations that expect one or the other.

Additionally, auth tokens and results of simple calls can be cached to further
reduce the number of commands and round trips needed to perform common tasks.


CLI User Input Parsing
----------------------

Parsing is done using argparse, largely auto-generated. For the majority of
cases, this will just look like ``ocl service_name method some_arg1 some_arg2`` .

Dash dash help (--help) works as expected at whichever level it is called
to give more granular information on calls.
