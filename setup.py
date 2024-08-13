from setuptools import setup, find_packages

setup(
    name='async_colab_module',
    version='0.0.1',
    packages=find_packages(),
    install_requires=['asyncio', 'aiohttp', 'aiolimiter', 'ipywidgets', 'ipython', 'pandas', 'openpyxl'],
    extras_require={
        "dev": ["pytest",],
    },
    include_package_data=True,
    author='Lubentsov Artem',
    author_email='artem.law@mail.ru',
    description='AsyncIntegration module MoySklad, WB',
    url='https://github.com/artemlaw/colab_module',
)