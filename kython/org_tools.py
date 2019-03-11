from datetime import datetime
import logging
from pathlib import Path
import re
from collections import OrderedDict
from typing import List, Optional, Dict

def date2org(t: datetime) -> str:
    return t.strftime("%Y-%m-%d %a")

def datetime2orgtime(t: datetime) -> str:
    return t.strftime("%H:%M")

def datetime2org(t: datetime) -> str:
    return date2org(t) + " " + datetime2orgtime(t)

def test_datetime2org():
    d = datetime.strptime('19920110 04:45', '%Y%m%d %H:%M')
    assert datetime2org(d) == '1992-01-10 Fri 04:45'

# TODO priority maybe??
# TODO need to sanitize!
def as_org_entry(
        heading: Optional[str] = None,
        tags: List[str] = [],
        body: Optional[str] = None,
        created: Optional[datetime]=None,
        inline_created=False,
        todo=True,
        level=1,
):
    if heading is None:
        if body is None:
            raise RuntimeError('Both heading and body are empty!!')
        heading = body.splitlines()[0] # TODO ??

    if body is None:
        body = ''

    # TODO FIXME escape everything properly!
    heading = re.sub(r'\s', ' ', heading)
    # TODO remove newlines from body

    NOW = datetime.now() # TODO tz??
    if created is None:
        created = NOW

    todo_s = ' TODO' if todo else ''
    tag_s = ':'.join(tags)

    sch = [f'  SCHEDULED: <{date2org(NOW)}>'] if todo else []

    if len(tag_s) != 0:
        tag_s = f':{tag_s}:'

    props: Dict[str, str] = OrderedDict()

    crs = f'[{datetime2org(created)}]'
    icr_s: str
    if inline_created:
        icr_s = ' ' + crs
    else:
        icr_s = ""
        props['CREATED'] = crs

    props_lines: List[str] = []
    if len(props) > 0:
        props_lines.append(':PROPERTIES:')
        props_lines.extend(f':{prop}: {value}' for prop, value in props.items())
        props_lines.append(':END:')

    lines = [
        '*' * level + f"""{todo_s}{icr_s} {heading} {tag_s}""",
        *sch,
        *props_lines,
        body,
    ]
    # TODO FIXME careful here, I guess actually need some tests for endlines
    return '\n'.join(lines)

def test_as_org_entry():
    # shouldn't crash at least
    as_org_entry(heading=None, tags=['hi'], body='whatever...', created=None, todo=False)

# TODO should we check if it exists first?
def append_org_entry(
        path: Path,
        *args,
        **kwargs,
):
    res = as_org_entry(*args, **kwargs)
    # https://stackoverflow.com/a/13232181
    if len(res.encode('utf8')) > 4096:
        logging.warning("writing out %s might be non-atomic", res)
    with path.open('a') as fo:
        fo.write(res)
