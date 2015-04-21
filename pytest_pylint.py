"""Pylint plugin for py.test"""
import pytest

from pylint import lint
from pylint.interfaces import IReporter
from pylint.reporters import BaseReporter


class ProgrammaticReporter(BaseReporter):
    """Reporter that replaces output with storage in list of dictionaries"""

    __implements__ = IReporter
    extension = 'prog'

    def __init__(self, output=None):
        BaseReporter.__init__(self, output)
        self.current_module = None
        self.data = []

    def add_message(self, msg_id, location, msg):
        """Get message and append to our data structure"""
        module, obj, line, col_offset = location[1:]
        self.data.append(dict(
            module=module,
            obj=obj,
            line=line,
            col_offset=col_offset,
            msg_id=msg_id[1:],
            msg_level=msg_id[0],
            msg=msg
        ))

    def _display(self, layout):
        """launch layouts display"""
        pass


def pytest_addoption(parser):
    group = parser.getgroup("general")
    group.addoption(
        "--pylint",
        action="store_true", default=False,
        help="run pylint on all"
    )
    group.addoption(
        '--pylint-rcfile',
        default=None,
        help='Location of RC file if not pylintrc'
    )
    group.addoption(
        '--pylint-error-types',
        default='CRWEF',
        help='The types of pylint errors to consider failures by letter'
        ', default is all of them (CRWEF).'
    )


def pytest_collect_file(path, parent):
    config = parent.config
    if path.ext == ".py":
        if config.option.pylint:
            return PyLintItem(path, parent)


class PyLintException(Exception):
    """Exception to raise if a file has a specified pylint error"""
    pass


class PyLintItem(pytest.Item, pytest.File):

    def runtest(self):
        reporter = ProgrammaticReporter()
        # Build argument list for pylint
        args_list = [unicode(self.fspath)]
        if self.config.option.pylint_rcfile:
            args_list.append('--rcfile={0}'.format(
                self.config.pylint_rcfile
            ))
        lint.Run(args_list, reporter=reporter, exit=False)
        for error in reporter.data:
            if error['msg_level'] in self.config.option.pylint_error_types:
                raise PyLintException(
                    '{msg_level}{msg_id}:{line},{col_offset}{obj}:'
                    '{msg}'.format(**error)
                )

    def repr_failure(self, excinfo):
        if excinfo.errisinstance(PyLintException):
            return excinfo.value.args[0]
        return super(PyLintItem, self).repr_failure(excinfo)

    def reportinfo(self):
        return self.fspath, None, "[pylint] {0}".format(self.name)
