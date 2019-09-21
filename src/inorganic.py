from datetime import datetime, date
import logging
from pathlib import Path
import re
from collections import OrderedDict
from typing import List, Optional, Dict, Union, Sequence

Dateish = Union[datetime, date]

def _sanitize(x: str) -> str:
    return re.sub(r'[\]\[]', '', x)


def sanitize_org_body(text: str) -> str:
    # TODO hmm. maybe just tabulating with 1 space is enough?...
    return ''.join(' ' + l for l in text.splitlines(keepends=True))


def sanitize_tag(tag: str) -> str:
    """
    >>> sanitize_tag('test-d@shes')
    'test_d@shes'
    """
    # https://orgmode.org/manual/Tags.html
    # Tags are normal words containing letters, numbers, ‘_’, and ‘@’.
    # TODO not sure, perhaps we want strict mode for formatting?
    # TODO reuse orgparse regexes?
    return re.sub(r'[^@\w]', '_', tag)

def link(url: Optional[str]=None, title: Optional[str]=None) -> str:
    assert url is not None
    assert title is not None
    # TODO FIXME how to sanitize properly
    title = _sanitize(title)
    url = _sanitize(url)
    return f'[[{url}][{title}]]'


def date2org(t: Dateish) -> str:
    return t.strftime("%Y-%m-%d %a")

def datetime2orgtime(t: datetime) -> str:
    return t.strftime("%H:%M")

def datetime2org(t: Dateish) -> str:
    """
    >>> dt = datetime.strptime('19920110 04:45', '%Y%m%d %H:%M')
    >>> datetime2org(dt)
    '1992-01-10 Fri 04:45'
    """
    r = date2org(t)
    if isinstance(t, datetime):
        r += " " + datetime2orgtime(t)
    return r


def org_dt(t: Dateish, inactive=False, active=False) -> str:
    beg, end = '', ''
    if inactive:
        beg, end = '[]'
    if active:
        beg, end = '<>'
    return beg + datetime2org(t) + end


# TODO priority maybe??
# TODO need to sanitize!
# TODO for sanitizing, have two strategies: error and replace
def as_org_entry(
        heading: Optional[str] = None,
        todo: Optional[str] = None,
        tags: Sequence[str] = [],
        scheduled: Optional[Dateish] = None,
        properties=None,
        body: Optional[str] = None,
        level=1,
):
    r"""
    >>> as_org_entry(heading=None, tags=['hi'], body='whatever...')
    '* :hi:\n whatever...'
    >>> as_org_entry(heading=None, todo=None, tags=(), level=2)
    '** '
    >>> as_org_entry(heading='heading', body=None)
    '* heading'
    >>> as_org_entry(heading='heading', body='keep\n newlines\n')
    '* heading\n keep\n  newlines\n'
    >>> as_org_entry(heading='123', todo='TODO', level=0)
    'TODO 123'
    >>> as_org_entry(heading='*abacaba', body='***whoops', tags=('baa@d tag', 'goodtag'))
    '* *abacaba :baa@d_tag:goodtag:\n ***whoops'
    """
    # TODO not great that we always pad body I guess. maybe needs some sort of raw_body argument?
    # TODO FIXME escape everything properly!
    if heading is None:
        heading = ''
    heading = re.sub(r'\s', ' ', heading)

    # TODO remove newlines from body?
    if body is not None:
        body = sanitize_org_body(body)


    parts = []

    if level > 0:
        parts.append('*' * level)

    if todo is not None:
        parts.append(todo)

    if len(heading) > 0:
        parts.append(heading)

    if len(tags) > 0:
        # tags_s = ('' if heading.endswith(' ') else ' ') +
        tags_s = ':' + ':'.join(map(sanitize_tag, tags)) + ':'
        parts.append(tags_s)

    sch_lines = [] if scheduled is None else [
        'SCHEDULED: ' + org_dt(scheduled, active=True)
    ]

    props_lines: List[str] = []
    props = {} if properties is None else properties
    if len(props) > 0:
        props_lines.append(':PROPERTIES:')
        props_lines.extend(f':{prop}: {value}' for prop, value in props.items())
        props_lines.append(':END:')

    body_lines = [] if body is None else [body]

    if len(parts) == 1:
        # means it's only got level stars, so we need to make sure space is present (otherwise it's not an outline)
        parts.append('')
    lines = [
        ' '.join(parts), # TODO just in case check that parts doesn't have newlines?
        *sch_lines,
        *props_lines,
        *body_lines,
    ]
    # TODO FIXME careful here, I guess actually need some tests for endlines
    return '\n'.join(lines)

# TODO get rid of this
def as_org(todo=None, **kwargs):
    res = as_org_entry(
        todo=todo,
        level=0,
        **kwargs,
    )
    return res


# TODO kython?...
from typing import TypeVar, Callable
T = TypeVar('T')
Lazy = Union[T, Callable[[], T]]

# meh
def from_lazy(x: Lazy[T]) -> T:
    if callable(x):
        return x()
    else:
        return x


from typing import NamedTuple, Optional, Sequence, Dict, Mapping, Any, Tuple
class OrgNode(NamedTuple):
    heading: Lazy[str] # TODO make body lazy as well?
    todo: Optional[str] = None
    tags: Sequence[str] = ()
    scheduled: Optional[Dateish] = None
    properties: Optional[Mapping[str, str]] = None
    body: Optional[str] = None
    children: Sequence[Any] = () # mypy wouldn't allow recursive type here...

    def render_self(self) -> str:
        return as_org_entry(
            heading=from_lazy(self.heading),
            todo=self.todo,
            tags=self.tags,
            properties=self.properties,
            scheduled=self.scheduled,
            body=self.body,
            level=0,
        )

    def render_hier(self) -> List[Tuple[int, str]]:
        res = [(0, self.render_self())]
        for ch in self.children:
            # TODO make sure there is a space??
            # TODO shit, would be nice to tabulate?.. not sure
            res.extend((l + 1, x) for l, x in ch.render_hier())
        return res

    def render(self, level=0) -> str:
        rh = self.render_hier()
        rh = [(level + l, x) for l, x in rh]
        return '\n'.join('*' * l + (' ' if l > 0 else '') + x for l, x in rh)

# TODO level -- I guess gonna be implicit...


def node(*args, **kwargs):
    return OrgNode(*args, **kwargs)


