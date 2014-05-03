from setuptools import setup

setup(
    name='flask_shadowsession',
    version='1.0.0',
    url='https://github.com/lovette/flask_shadowsession',
	download_url = 'https://github.com/lovette/flask_shadowsession/archive/master.tar.gz',
    license='BSD',
    author='Lance Lovette',
    author_email='lance.lovette@gmail.com',
    description='Flask extension that creates a "shadow session" using Redis hash as a dictionary.',
    long_description=open('README.md').read(),
    py_modules=['flask_shadowsession',],
    install_requires=['Flask', 'redis', 'flask_redisdict',],
    tests_require=['nose',],
    zip_safe=False,
    platforms='any',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
