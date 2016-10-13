# *ordereddict* module for Package Control


This is the *[ordereddict][]* module
with the `OrderedDict` class
bundled for usage with [Package Control][],
a package manager
for the [Sublime Text][] text editor.


this repo | pypi 
---- | ----
![latest tag](https://img.shields.io/github/tag/packagecontrol/ordereddict.svg) | [![pypi](https://pypip.in/version/ordereddict/badge.svg)][pypi]


## How to use *ordereddict* as a dependency

In order to tell Package Control
that you are using the *ordereddict* module
in your ST package,
create a `dependencies.json` file
in your package root
with the following contents:

```js
{
   "*": {
      "<3000": [
         "ordereddict"
      ]
   }
}
```

If the file exists already,
add `"ordereddict"` to the every `"<3000"` dependency list.

Then run the **Package Control: Satisfy Dependencies** command
to make Package Control
install the module for you locally
(if you don't have it already).

After all this
you can use
`from ordereddict import OrderedDict`
in any of your Python plugins,
on ST2.

Code that will work
in both ST2 and ST3:

```py
try:
   from ordereddict import OrderedDict
except ImportError:
   from collections import OrderedDict
```

See also:
[Documentation on Dependencies](https://packagecontrol.io/docs/dependencies)


## License

The contents of the root folder
in this repository
(just `README.md`)
are released
under the *public domain*.
The contents of the `st2/` folder
fall under *their own bundled licenses*.


[ordereddict]: http://docs.python-ordereddict.org/en/latest/
[Package Control]: http://packagecontrol.io/
[Sublime Text]: http://sublimetext.com/
[pypi]: https://pypi.python.org/pypi/ordereddict
