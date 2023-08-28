__all__ = (
    "get_installed_packages",
    "install_all_packages"
)

from typing import Iterable, Callable, TYPE_CHECKING
from argostranslate.package import (
    get_available_packages, 
    update_package_index,
    get_installed_packages
)
from concurrent.futures import ThreadPoolExecutor
if TYPE_CHECKING:
    from argostranslate.package import AvailablePackage
    from pathlib import Path

def install_all_packages(
        excluded_languages: Iterable[str] = (),
        excluded_translations: Iterable[tuple[str,str]] = (),
        callback: Callable[[int, int], None] = lambda a, b: None
    ) -> int:
    """
    Installs all available language packages
    This process is task-based using multithreading

    Parameters
    ----------
    + excluded_languages: `Iterable[str]`
        Codes for languages whose to or from translations should not be 
        installed
    + excluded_translations: `Iterable[tuple[str,str]]`
        Translation codes in (from, to) order. These packages will not
        be installed
    """
    packages = list(filter(
        lambda package:
            package.from_code not in excluded_languages 
            or package.to_code not in excluded_languages
            or (package.from_code, package.to_code) 
                not in excluded_translations
        ,
        get_new_packages()
    ))
    completed_installs = 0
    def _install(package: "AvailablePackage"):
        nonlocal completed_installs
        package.install()
        completed_installs += 1
        callback(completed_installs,len(packages))
    if len(packages) > 0:
        with ThreadPoolExecutor() as pool:
            pool.map(
                _install, 
                packages
            )
    return len(packages)

def get_new_packages(path: "Path"=None) -> list["AvailablePackage"]:
    """
    Gets all updatable or new packages from the index.
    This function does not install any new packages.

    Parameters
    ----------
    + path: `Path`
        The path to look for packages in.
        Will default to argostranslate's default.
    """
    update_package_index()
    # Packages are non-hashable objects :(
    installed_packages = get_installed_packages(path)
    available_packages = get_available_packages()
    return [
        package 
        for package in available_packages 
        if package not in installed_packages
    ]