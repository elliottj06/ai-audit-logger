from setuptools import setup, find_packages

setup(
    name="ai-audit-logger",
    version="0.1.0",
    description="Drop-in audit logging for LLM API calls (OpenAI, Anthropic)",
    long_description=open("../../README.md").read(),
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
    ],
)
