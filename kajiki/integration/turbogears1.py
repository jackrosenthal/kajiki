"""Kajiki template plugin for TurboGears 1

Available configuration options (passed in from TurboGears; defaults listed in
parentheses):

    kajiki.loader_class     Loader implementation; should be a fully-qualified
                            dotted class name ('kajiki.loader.PackageLoader')
    kajiki.reload           Automatically reload changed templates (True)
    kajiki.force_mode       Force the template rendering mode; one of 'txt',
                            'xml', 'html', or 'html5' (None)

Modeled on Genshi's template engine plugin and tested with TG1.5; YMMV for
other versions.

"""

from kajiki import PackageLoader
from kajiki.xml_template import XMLTemplate


class ConfigurationError(ValueError):
    """Exception raised on invalid options."""


class XMLTemplateEnginePlugin(object):
    template_class = XMLTemplate

    def __init__(self, extra_vars_func=None, engine_options=None):
        engine_options = engine_options or {}
        self.get_extra_vars = extra_vars_func

        loader_options = {
            'reload': engine_options.get('kajiki.reload', True),
            'force_mode': engine_options.get('kajiki.force_mode')
        }

        Loader = PackageLoader
        custom_loader = engine_options.get('kajiki.loader_class')

        if custom_loader:
            Loader = self._import_loader(custom_loader)

        self.loader = Loader(**loader_options)

    def _import_loader(self, custom_loader):
        try:
            module_name, class_name = custom_loader.rsplit('.', 1)
            module = __import__(module_name, fromlist=[class_name])
            return getattr(module, class_name)
        except:
            raise ConfigurationError(
                'Couldn\'t import loader class "{}"; '.format(custom_loader) +
                'kajiki.loader_class should be a fully-qualified dotted '
                'class name'
            )

    def load_template(self, templatename, template_string=None):
        """Find a template specified in python 'dot' notation, or load one
        from a string."""

        if template_string is not None:
            return self.template_class(template_string)
        else:
            return self.loader.load(templatename)

    def render(self, info, fragment=False, format=None, template=None):
        """Render the template to a string."""

        return self.transform(info, template).render()

    def transform(self, info, template):
        """Create a template object"""

        if isinstance(template, basestring):
            template = self.load_template(template)

        info.update(self.get_extra_vars())
        return template(info)
