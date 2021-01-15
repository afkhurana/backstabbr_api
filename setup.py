from setuptools import setup, find_packages

setup(name='backstabbr_api',
		version='1.0.0',
		description='Web-scraper API and Discord Bot for the online diplomacy program Backstabbr',
		url='https://github.com/afkhurana/backstabbr_api',
		author='Arjun Khurana',
		author_email='afkhurana@gmail.com',
		license='MIT',
		packages=['backstabbr_api', 'backstabbr_bot'],
		install_requires=["discord.py", "html5print", "requests"])
