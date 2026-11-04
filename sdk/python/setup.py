from setuptools import setup, find_packages
import os

try:
    readme = open(os.path.join(os.path.dirname(__file__), "../../README.md"), encoding="utf-8").read()
except FileNotFoundError:
    readme = "Drop-in audit logging for LLM API calls (OpenAI, Anthropic)"

setup(
    name="ai-audit-logger",
    version="0.1.1",
    description="Drop-in audit logging for LLM API calls (OpenAI, Anthropic)",
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "httpx>=0.24.0",
    ],
    extras_require={
        "openai": ["openai>=1.0.0"],
        "anthropic": ["anthropic>=0.20.0"],
        "all": ["openai>=1.0.0", "anthropic>=0.20.0"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Logging",
        "Intended Audience :: Developers",
    ],
    keywords="llm openai anthropic audit logging ai compliance observability",
    project_urls={
        "Source": "https://github.com/elliottj06/ai-audit-logger",
        "Bug Tracker": "https://github.com/elliottj06/ai-audit-logger/issues",
    },
)
