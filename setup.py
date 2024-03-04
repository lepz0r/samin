from distutils.core import setup

setup(
    name="samin",
    version="0.01",
    author="lepz0r",
    author_email="punkofthedeath@gmail.com",
    packages=["samin"],
    url="https://gitlab.com/lepz0r/samin",
    license="GPL-2",
    description="A btrfs snapshot utility",
    install_requires=["psutil", "pytz", "tzlocal"],
    entry_points={
        "console_scripts": [
            "samin = samin.__main__:main_func",
        ]
    },
)
