# -*- coding: utf-8 -*-

from . import six
from .six import text_type
from .util import parse_timestamp


class List(object):
    """Base class for lazy object iteration

    This is a class providing lazy iteration.  This means that the
    content is loaded in chunks as long as the response hints at
    continuing content.
    """

    def __init__(self, site, list_name, prefix, limit=None, return_values=None, max_items=None, *args, **kwargs):
        # NOTE: Fix limit
        self.site = site
        self.list_name = list_name
        self.generator = 'list'
        self.prefix = prefix

        kwargs.update(args)
        self.args = kwargs

        if limit is None:
            limit = site.api_limit
        self.args[self.prefix + 'limit'] = text_type(limit)

        self.count = 0
        self.max_items = max_items

        self._iter = iter(six.moves.range(0))

        self.last = False
        self.result_member = list_name
        self.return_values = return_values

    def __iter__(self):
        return self

    def __next__(self):
        if self.max_items is not None:
            if self.count >= self.max_items:
                raise StopIteration
        try:
            item = six.next(self._iter)
        except StopIteration:
            if self.last:
                raise
            self.load_chunk()
            item = six.next(self._iter)

        self.count += 1
        if 'timestamp' in item:
            item['timestamp'] = parse_timestamp(item['timestamp'])

        if isinstance(self, GeneratorList):
            return item
        if type(self.return_values) is tuple:
            return tuple((item[i] for i in self.return_values))
        if self.return_values is not None:
            return item[self.return_values]
        return item

    def next(self, *args, **kwargs):
        """ For Python 2.x support """
        return self.__next__(*args, **kwargs)

    def load_chunk(self):
        """Query a new chunk of data

        If the query is empty, `raise StopIteration`.

        Else, update the iterator accordingly.

        If 'continue' is in the response, it is added to `self.args`
        (new style continuation, added in MediaWiki 1.21).

        If not, but 'query-continue' is in the response, query its
        item called `self.list_name` and add this to `self.args` (old
        style continuation).

        Else, set `self.last` to True.
        """
        data = self.site.api(
            'query', (self.generator, self.list_name),
            *[(text_type(k), v) for k, v in six.iteritems(self.args)]
        )
        if not data:
            # Non existent page
            raise StopIteration
        self.set_iter(data)

        if data.get('continue'):
            # New style continuation, added in MediaWiki 1.21
            self.args.update(data['continue'])

        elif self.list_name in data.get('query-continue', ()):
            # Old style continuation
            self.args.update(data['query-continue'][self.list_name])

        else:
            self.last = True

    def set_iter(self, data):
        """Set `self._iter` to the API response `data`."""
        if self.result_member not in data['query']:
            self._iter = iter(six.moves.range(0))
        elif type(data['query'][self.result_member]) is list:
            self._iter = iter(data['query'][self.result_member])
        else:
            self._iter = six.itervalues(data['query'][self.result_member])

    def __repr__(self):
        return "<List object '%s' for %s>" % (self.list_name, self.site)

    @staticmethod
    def generate_kwargs(_prefix, *args, **kwargs):
        kwargs.update(args)
        for key, value in six.iteritems(kwargs):
            if value is not None and value is not False:
                yield _prefix + key, value

    @staticmethod
    def get_prefix(prefix, generator=False):
        return ('g' if generator else '') + prefix

    @staticmethod
    def get_list(generator=False):
        return GeneratorList if generator else List


class NestedList(List):
    def __init__(self, nested_param, *args, **kwargs):
        super(NestedList, self).__init__(*args, **kwargs)
        self.nested_param = nested_param

    def set_iter(self, data):
        self._iter = iter(data['query'][self.result_member][self.nested_param])


class GeneratorList(List):
    """Lazy-loaded list of Page, Image or Category objects

    While the standard List class yields raw response data
    (optionally filtered based on the value of List.return_values),
    this subclass turns the data into Page, Image or Category objects.
    """

    def __init__(self, site, list_name, prefix, *args, **kwargs):
        super(GeneratorList, self).__init__(site, list_name, prefix,
                                            *args, **kwargs)

        self.args['g' + self.prefix + 'limit'] = self.args[self.prefix + 'limit']
        del self.args[self.prefix + 'limit']
        self.generator = 'generator'

        self.args['prop'] = 'info|imageinfo'
        self.args['inprop'] = 'protection'

        self.result_member = 'pages'

        from .page import Page
        from .image import Image
        from .category import Category

        self.page_class = Page
        self.image_class = Image
        self.category_class = Category

    def __next__(self):
        info = super(GeneratorList, self).__next__()
        if info['ns'] == 14:
            return self.category_class(self.site, u'', info)
        if info['ns'] == 6:
            return self.image_class(self.site, u'', info)
        return self.page_class(self.site, u'', info)

    def next(self):
        """ For Python 2.x support """
        return self.__next__()

    def load_chunk(self):
        # Put this here so that the constructor does not fail
        # on uninitialized sites
        self.args['iiprop'] = 'timestamp|user|comment|url|size|sha1|metadata|archivename'
        return super(GeneratorList, self).load_chunk()


class PageList(GeneratorList):

    def __init__(self, site, prefix=None, start=None, namespace=0, redirects='all', end=None):
        self.namespace = namespace

        kwargs = {}
        if prefix:
            kwargs['gapprefix'] = prefix
        if start:
            kwargs['gapfrom'] = start
        if end:
            kwargs['gapto'] = end

        super(PageList, self).__init__(site, 'allpages', 'ap',
                                       gapnamespace=text_type(namespace),
                                       gapfilterredir=redirects,
                                       **kwargs)

    def __getitem__(self, name):
        return self.get(name, None)

    def get(self, name, info=()):
        if self.namespace == 14:
            return self.category_class(self.site, self.site.namespaces[14] + ':' + name, info)
        elif self.namespace == 6:
            return self.image_class(self.site, self.site.namespaces[6] + ':' + name, info)
        elif self.namespace != 0:
            return self.page_class(self.site, self.site.namespaces[self.namespace] + ':' + name, info)
        else:
            # Guessing page class
            if type(name) is not int:
                namespace = self.guess_namespace(name)
                if namespace == 14:
                    return self.category_class(self.site, name, info)
                elif namespace == 6:
                    return self.image_class(self.site, name, info)

            return self.page_class(self.site, name, info)

    def guess_namespace(self, name):
        """Guess the namespace from name

        If name starts with any of the site's namespaces' names or
        default_namespaces, use that.  Else, return zero.

        Args:
            name (str): The pagename as a string (having `.startswith`)

        Returns:
            The id of the guessed namespace or zero.
        """
        for ns in self.site.namespaces:
            if ns == 0:
                continue
            if name.startswith(u'%s:' % self.site.namespaces[ns].replace(' ', '_')):
                return ns
            elif ns in self.site.default_namespaces:
                if name.startswith(u'%s:' % self.site.default_namespaces[ns].replace(' ', '_')):
                    return ns
        return 0


class PageProperty(List):

    def __init__(self, page, prop, prefix, *args, **kwargs):
        super(PageProperty, self).__init__(page.site, prop, prefix,
                                           titles=page.name,
                                           *args, **kwargs)
        self.page = page
        self.generator = 'prop'

    def set_iter(self, data):
        for _page in six.itervalues(data['query']['pages']):
            if _page['title'] == self.page.name:
                self._iter = iter(_page.get(self.list_name, ()))
                return
        raise StopIteration


class PagePropertyGenerator(GeneratorList):

    def __init__(self, page, prop, prefix, *args, **kwargs):
        super(PagePropertyGenerator, self).__init__(page.site, prop, prefix,
                                                    titles=page.name,
                                                    *args, **kwargs)
        self.page = page


class RevisionsIterator(PageProperty):

    def load_chunk(self):
        if 'rvstartid' in self.args and 'rvstart' in self.args:
            del self.args['rvstart']
        return super(RevisionsIterator, self).load_chunk()