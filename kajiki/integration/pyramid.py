"""This module integrates the Kajiki_ templating language into the
Pyramid_ web framework.

To enable it, add this to your Pyramid web app configuration::

    config.include('kajiki.integration.pyramid')

Also add something like the following to the
application section of your Pyramid application's .ini file::

    [app:yourapp]
    # ... other stuff ...
    pyramid.reload_templates = True
    kajiki.extensions = .kajiki .genshi
    # The Kajiki output mode can be "html5", "html" or "xml"
    kajiki.mode = html5

Then configure your views just like the other Pyramid templating
languages, passing an asset specification to the ``renderer`` argument::

    @view_config(route_name='faq', renderer='app:templates/faq-page.kajiki')

* TODO: Support text templates, too.
* TODO: i18n

.. _`Kajiki`: http://pypi.python.org/pypi/Kajiki/
.. _`Pyramid`: http://docs.pylonshq.com/
"""

from os import stat

from paste.deploy.converters import asbool
from pyramid.interfaces import IRenderer, ITemplateRenderer
from pyramid.resource import abspath_from_resource_spec
from zope.interface import implementer

from kajiki import XMLTemplate
from kajiki.loader import Loader


def includeme(config):
    """Sets up the Kajiki templating language for the configured
    file extensions.
    """
    if hasattr(config.registry, "kajiki_loader"):
        return  # Include only once per config
    settings = config.get_settings()
    extensions = settings.get("kajiki.extensions", ".kajiki").split()
    for extension in extensions:
        config.add_renderer(extension, renderer_factory)
    config.registry.kajiki_loader = PyramidKajikiLoader(
        auto_reload=asbool(settings.get("pyramid.reload_templates")),
        mode=settings.get("kajiki.mode", "html5"),
    )


@implementer(ITemplateRenderer)
@implementer(IRenderer)
class PyramidKajikiLoader(Loader):
    """Yet another template loader; this one specializes in resource specs."""

    def implementation(self):  # ITemplateRenderer implementation
        return self

    def __init__(self, auto_reload=False, mode="html5"):
        self.auto_reload = auto_reload
        self.mode = mode
        self._timestamps = {}
        super().__init__()

    def _load(self, name, *a, **kw):
        """Called when the template actually needs to be (re)compiled."""
        return XMLTemplate(source=None, filename=name, mode=self.mode, *a, **kw)

    def import_(self, name, *a, **kw):
        """Overrides Loader.import_().

        * Resolves the resource spec into an absolute path for the template.
        * Checks the template modification time to decide whether to reload it.
        """
        name = abspath_from_resource_spec(name)
        if self.auto_reload and name in self.modules:
            mtime = stat(name).st_mtime
            if mtime > self._timestamps.get(name, 0):
                del self.modules[name]
        return super().import_(name, *a, **kw)

    def __call__(self, value, system, is_fragment=False):
        """IRenderer implementation.

        ``value`` is the result of the view.
        Returns a result (a string or unicode object useful as
        a response body). Values computed by
        the system are passed by the system in the ``system``
        parameter, which is a dictionary. Keys in the dictionary
        include: ``view`` (the view callable that returned the value),
        ``renderer_name`` (the template name or simple name of the
        renderer), ``context`` (the context object passed to the
        view), and ``request`` (the request object passed to the
        view).
        """
        name = system.get("renderer_name") or system["renderer_info"].name
        template = self.import_(name, is_fragment=is_fragment)
        try:
            system.update(value)
        except (TypeError, ValueError):
            raise ValueError(
                "The Kajiki template renderer was passed a " "non-dictionary as value."
            )
        # self._save_template_as_python(template, system, name)  # to debug
        return template(system).render()

    def _save_template_as_python(
        self, template, context, name, dir="kajiki_debug", encoding="utf-8"
    ):
        "Just a debugging device used in the development of Kajiki itself."
        from codecs import open
        from os import makedirs, path

        makedirs(dir, exist_ok=True)
        path = path.join(dir, name.replace(":", "-").replace("/", "_") + ".py")
        with open(path, "w", encoding=encoding) as f:
            f.write(template(context).py_text)
        print("Compiled Kajiki template written to " + path)

    def fragment(self, renderer_name, dic, view=None, request=None):
        """Example usage from a class-based view:

        html_fragment = request.registry.kajiki_loader.fragment(
            'myapp:templates/fragment_template.kajiki',
            a_dictionary_used_as_template_context,
            view=self)
        """
        return self(
            is_fragment=True,
            value=dic,
            system=dict(
                renderer_name=renderer_name,
                request=request or view.request,
                view=view,
                context=dic,
            ),
        )


def renderer_factory(info):
    """*info* contains::

    name = Attribute('The value passed by the user as the renderer name')
    package = Attribute('The "current package" when the renderer '
                        'configuration statement was found')
    type = Attribute('The renderer type name')
    registry = Attribute('The "current" application registry when the '
                         'renderer was created')
    settings = Attribute('The ISettings dictionary related to the '
                         'current app')
    """
    return info.registry.kajiki_loader
