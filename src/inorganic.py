from datetime import datetime, date
import logging
from pathlib import Path
import re
from collections import OrderedDict
from typing import List, Optional, Dict, Union

Dateish = Union[datetime, date]

def _sanitize(x: str) -> str:
    return re.sub(r'[\]\[]', '', x)


def sanitize_org_body(text: str) -> str:
    # TODO hmm. maybe just tabulating with 1 space is enough?...
    return ''.join(' ' + l for l in text.splitlines(keepends=True))


def sanitize_tag(tag: str) -> str:
    # https://orgmode.org/manual/Tags.html
    # Tags are normal words containing letters, numbers, ‘_’, and ‘@’.
    # TODO not sure, perhaps we want strict mode for formatting?
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


def test_datetime2org():
    d = datetime.strptime('19920110 04:45', '%Y%m%d %H:%M')
    assert datetime2org(d) == '1992-01-10 Fri 04:45'

# TODO priority maybe??
# TODO need to sanitize!
# TODO for sanitizing, have two strategies: error and replace
from typing import Sequence
def as_org_entry(
        heading: Optional[str] = None,
        todo: Optional[str] = None,
        tags: Sequence[str] = [],
        scheduled: Optional[datetime] = None,
        properties=None,
        body: Optional[str] = None,
        created: Optional[Dateish]=None,
        inline_created=False,
        active_created=False,
        force_no_created=False,
        level=1,
):
    assert created is None, 'created is deprecated'
    # TODO FIXME don't do that?
    if heading is None:
        if body is None:
            raise RuntimeError('Both heading and body are empty!!')
        heading = body.splitlines()[0] # TODO ??

    if body is not None:
        body = sanitize_org_body(body)

    # TODO FIXME escape everything properly!
    heading = re.sub(r'\s', ' ', heading)
    # TODO remove newlines from body

    parts = []

    if level > 0:
        parts.append('*' * level)

    if todo is not None:
        parts.append(todo)

    # TODO hacky, not sure...
    # sch = [f'  SCHEDULED: <{date2org(NOW)}>'] if todo == 'TODO' else []

    props = {} if properties is None else properties

    parts.append(heading)

    tags_s = ':'.join(map(sanitize_tag, tags))
    if len(tags_s) > 0:
        parts.append(f':{tags_s}:')

    sch_lines = [] if scheduled is None else ['SCHEDULED: ' + org_dt(scheduled, active=True)]

    props_lines: List[str] = []
    if len(props) > 0:
        props_lines.append(':PROPERTIES:')
        props_lines.extend(f':{prop}: {value}' for prop, value in props.items())
        props_lines.append(':END:')

    body_lines = [] if body is None else [body]

    # TODO not sure... not super consistent
    lines = [
        ' '.join(parts), # TODO just in case check that parts doesn't have newlines?
        *sch_lines,
        *props_lines,
        *body_lines,
    ]
    # TODO FIXME careful here, I guess actually need some tests for endlines
    return '\n'.join(lines)


def test_as_org_entry():
    # shouldn't crash at least
    as_org_entry(heading=None, tags=['hi'], body='whatever...', created=None, todo=None)


def test_as_org_entry_0():
    eee = as_org_entry(heading='123', created=None, todo='TODO', level=0)
    assert eee.startswith('TODO 123')


def test_santize():
    ee = as_org_entry(
        heading='aaaaa',
        body='**** what about that?',
        tags=['ba@@d tag', 'goodtag'],
        force_no_created=True,
        todo=None,
    )
    assert ee == """
* aaaaa :ba@@d_tag:goodtag:
 **** what about that?
""".strip()


def test_body():
    b = as_org_entry(
        heading='heading',
        body='please\nkeep newlines\n',
        force_no_created=True,
        todo=None,
    )
    assert b == """* heading
 please
 keep newlines
"""


def test_no_body():
    b = as_org_entry(
        heading='heading',
        body=None,
        force_no_created=True,
        todo=None,
    )
    assert b == """* heading"""


def test_todo():
    b = as_org_entry(
        heading='hi',
        todo='TODO',
        force_no_created=True,
        body='fewfwef\nfewfwf'
    )
    assert b.startswith("""* TODO hi""")


# TODO get rid of this
def as_org(todo=None, inline_created=True, **kwargs):
    res = as_org_entry(
        todo=todo,
        inline_created=inline_created,
        level=0,
        **kwargs,
    )
    return res

from typing import NamedTuple, Optional, Sequence, Dict, Mapping, Any, Tuple
# TODO what was the need for lazy?
class OrgNode(NamedTuple):
    heading: str
    todo: Optional[str] = None
    tags: Sequence[str] = ()
    scheduled: Optional[datetime] = None
    properties: Optional[Mapping[str, str]] = None
    body: Optional[str] = None
    children: Sequence[Any] = () # mypy wouldn't allow recursive type here...

    def render_self(self) -> str:
        return as_org_entry(
            heading=self.heading,
            todo=self.todo,
            tags=self.tags,
            properties=self.properties,
            scheduled=self.scheduled,
            body=self.body,
            force_no_created=True,
            inline_created=True,
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


def node(**kwargs):
    return OrgNode(**kwargs)


