# scripts/patch_imports.py
import sys
import collections.abc
import asyncio

# Fix collections.abc
if sys.version_info >= (3, 10):
    collections.MutableMapping = collections.abc.MutableMapping

# Fix asyncio.coroutine
if not hasattr(asyncio, 'coroutine'):
    asyncio.coroutine = asyncio.coroutines.coroutine

sys.modules['collections'] = collections
sys.modules['asyncio'] = asyncio