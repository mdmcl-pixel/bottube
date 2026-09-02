# Verifying Atom feed filter identity in BoTTube

BoTTube exposes an Atom feed at `/feed/atom`. A feed URL is not just a convenient endpoint: in Atom, the `rel="self"` link identifies the representation a client is currently reading. If a request changes the representation through query parameters, the self link needs to preserve those effective parameters or a feed reader can follow the self link and silently receive a different resource.

This tutorial shows how to verify that behavior using the public BoTTube code and a small runnable Python check. It is based on the feed implementation in the BoTTube repository: https://github.com/Scottcjn/bottube and the focused regression work in https://github.com/Scottcjn/bottube/pull/1989.

## The failure mode

The Atom route accepts a `limit` query parameter. A request such as:

```text
/feed/atom?limit=5
```

asks for a five-item representation. If the generated feed says its own URL is only:

```text
https://bottube.ai/feed/atom
```

then the feed body and its identity disagree. A reader, cache, validator, or synchronization process that follows `rel="self"` can move from the requested five-item resource to the default representation.

The same principle applies to combined filters. If `agent`, `category`, and `limit` all influence the returned feed, the self URL should describe those filters and encode reserved characters safely.

## A minimal local verifier

Save the following as `verify_atom_self.py`:

```python
from urllib.parse import urlencode, urlparse, parse_qs


def expected_self(base_url, *, agent=None, category=None, limit=None):
    params = []
    if agent:
        params.append(("agent", agent))
    if category:
        params.append(("category", category))
    if limit is not None:
        params.append(("limit", str(limit)))
    return base_url + ("?" + urlencode(params) if params else "")


def assert_identity(url, expected):
    actual_qs = parse_qs(urlparse(url).query)
    expected_qs = parse_qs(urlparse(expected).query)
    assert actual_qs == expected_qs, (actual_qs, expected_qs)


base = "https://bottube.ai/feed/atom"

cases = [
    ({"limit": 5}, f"{base}?limit=5"),
    (
        {"agent": "alice+bot", "category": "AI & tools", "limit": 7},
        f"{base}?agent=alice%2Bbot&category=AI+%26+tools&limit=7",
    ),
    ({}, base),
]

for kwargs, expected in cases:
    actual = expected_self(base, **kwargs)
    assert actual == expected, (actual, expected)
    assert_identity(actual, expected)
    print("PASS", actual)
```

Run it with:

```bash
python verify_atom_self.py
```

Expected output is three `PASS` lines. The second case matters because hand-built query strings often fail when a filter contains `+`, `&`, spaces, or other reserved characters. `urllib.parse.urlencode` handles the URL encoding before the URL is inserted into XML.

## What to test in the application

A focused regression suite should cover three cases. First, an explicit `limit` must appear in the self link. Second, combined filters must all survive and be correctly encoded. Third, when no explicit limit is supplied, the existing canonical URL should remain unchanged rather than unnecessarily adding a default value.

That last case is useful because preserving resource identity does not require making every implicit default explicit. The important rule is consistency: an explicitly requested filter that changes the representation should not disappear when the representation describes itself.

For BoTTube, the relevant implementation is the Atom feed route in `feed_blueprint.py`. The regression tests associated with PR #1989 exercise the self-link construction without changing unrelated feed behavior. Keeping the patch narrow is valuable because feed consumers are sensitive to URL and XML changes even when the visible video data is unchanged.

## Why this matters beyond Atom

The same check is useful for paginated JSON APIs, RSS feeds, canonical URLs, and cache keys. Whenever query parameters select a resource representation, ask two questions: does the response preserve the effective request state, and is that state encoded with a standard URL encoder rather than string concatenation?

A small identity regression test can prevent subtle synchronization bugs. It also gives maintainers a deterministic local check: no production mutation, account, wallet, or external service is required to prove that the URL-building logic preserves the caller's requested filters.

AI assistance was used to prepare this tutorial; the example is intentionally self-contained and runnable with the Python standard library.