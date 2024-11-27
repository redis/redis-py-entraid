#!/usr/bin/env python
from setuptools import find_packages, setup

setup(
    name="redispy-entraid-credentials",
    version="0.0.1",
    description="Entra ID credentials provider implementation for Redis-py client",
    packages=find_packages(
        include=["entraid"],
        exclude=["tests", ".github"]
    ),
    install_requires=[
        "redispyauth-prototype @ git+https://github.com/redis-developer/redispy-entraid-prototype.git/@tba",
        "redis @ git+https://github.com/redis/redis-py.git/@vv-tba-support",
        "PyJWT~=2.9.0",
        "msal~=1.31.0"
    ],
    url="https://github.com/redis-developer/redispy-entra-credentials",
    author="Redis Inc.",
    author_email="oss@redis.com",
)