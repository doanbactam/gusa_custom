from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="gusa_custom",
    version="0.1.0",
    description="GUSA Vietnam operations customizations for ERPNext",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="GUSA Vietnam",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[],
)
